from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.views.decorators.csrf import ensure_csrf_cookie
from .models import ChatRoom, ChatMessage, ChatAttachment, Order, VerificationRequest
from datetime import datetime
import os
import json
import logging

logger = logging.getLogger(__name__)

@login_required
@require_POST
@ensure_csrf_cookie
def request_verification(request):
    try:
        logger.info(f"Received verification request from user {request.user.username}")
        
        # Parse JSON data
        try:
            data = json.loads(request.body)
            chat_room_id = data.get('chat_room_id')
            verification_type = data.get('type')
            
            logger.info(f"Request data - chat_room_id: {chat_room_id}, type: {verification_type}")
        except json.JSONDecodeError:
            logger.error("Invalid JSON data received")
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid JSON data'
            }, status=400)
        
        if not chat_room_id or not verification_type:
            logger.error("Missing required fields in request")
            return JsonResponse({
                'status': 'error',
                'message': 'Missing required fields: chat_room_id or type'
            }, status=400)
        
        # Get chat room
        try:
            chat_room = ChatRoom.objects.get(id=chat_room_id)
            logger.info(f"Found chat room: {chat_room.id}")
        except ChatRoom.DoesNotExist:
            logger.error(f"Chat room not found: {chat_room_id}")
            return JsonResponse({
                'status': 'error',
                'message': 'Chat room not found'
            }, status=404)
        
        # Check if user is the lender
        if request.user != chat_room.order.product.user:
            logger.warning(f"User {request.user.username} attempted to request verification but is not the lender")
            return JsonResponse({
                'status': 'error',
                'message': 'Only lenders can request verification'
            }, status=403)
        
        # Check if there's already a pending request
        existing_request = VerificationRequest.objects.filter(
            chat_room=chat_room,
            type=verification_type,
            status='pending'
        ).exists()
        
        if existing_request:
            logger.info(f"Found existing pending request for {verification_type}")
            return JsonResponse({
                'status': 'error',
                'message': f'A pending {verification_type} verification request already exists'
            }, status=400)
            
        # Create verification request
        try:
            verification_request = VerificationRequest.objects.create(
                chat_room=chat_room,
                type=verification_type,
                status='pending'
            )
            logger.info(f"Created verification request {verification_request.id} of type {verification_type}")
            
            # Create a message in the chat
            ChatMessage.objects.create(
                chat_room=chat_room,
                sender=request.user,
                message=f'Requested {verification_type.replace("_", " ")} verification',
                message_type='verification_request'
            )
            logger.info(f"Created chat message for verification request {verification_request.id}")
            
            return JsonResponse({
                'status': 'success',
                'message': f'{verification_type.title()} verification request sent successfully'
            })
            
        except Exception as e:
            logger.error(f"Error creating verification request: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': 'Error creating verification request'
            }, status=500)
            
    except Exception as e:
        logger.error(f"Unexpected error in request_verification: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
@require_POST
@ensure_csrf_cookie
def submit_verification(request):
    try:
        logger.info(f"Received verification submission from user {request.user.username}")
        logger.info(f"POST data: {request.POST}")
        logger.info(f"FILES data: {request.FILES}")
        
        chat_room_id = request.POST.get('chat_room_id')
        verification_type = request.POST.get('type')
        
        if not chat_room_id or not verification_type:
            logger.error("Missing required fields in request")
            return JsonResponse({
                'status': 'error',
                'message': 'Missing required fields: chat_room_id or type'
            }, status=400)
        
        try:
            chat_room = ChatRoom.objects.get(id=chat_room_id)
            logger.info(f"Found chat room: {chat_room.id}")
        except ChatRoom.DoesNotExist:
            logger.error(f"Chat room not found: {chat_room_id}")
            return JsonResponse({
                'status': 'error',
                'message': 'Chat room not found'
            }, status=404)
        
        # Check if user is the borrower
        if request.user != chat_room.order.user:
            logger.warning(f"User {request.user.username} attempted to submit verification but is not the borrower")
            return JsonResponse({
                'status': 'error',
                'message': 'Only borrowers can submit verification'
            }, status=403)
            
        # Get all pending verification requests of this type and mark previous ones as cancelled
        pending_requests = VerificationRequest.objects.filter(
            chat_room=chat_room,
            type=verification_type,
            status='pending'
        ).order_by('-created_at')
        
        if not pending_requests.exists():
            logger.error(f"No pending verification request found for type {verification_type}")
            return JsonResponse({
                'status': 'error',
                'message': 'No pending verification request found'
            }, status=404)
            
        # Get the latest request and cancel others
        verification_request = pending_requests.first()
        pending_requests.exclude(id=verification_request.id).update(status='cancelled')
        
        # Handle file upload based on verification type
        try:
            if verification_type == 'govt_id':
                if 'govt_id' in request.FILES:
                    govt_id = request.FILES['govt_id']
                    # Validate file type
                    if not govt_id.content_type.startswith('image/'):
                        return JsonResponse({
                            'status': 'error',
                            'message': 'Please upload a valid image file'
                        }, status=400)
                    
                    verification_request.id_document = govt_id
                    verification_request.status = 'completed'
                    verification_request.acceptance_status = 'pending'
                    verification_request.save()
                    logger.info(f"Saved government ID file for verification request {verification_request.id}")
                else:
                    logger.error("Government ID file not provided")
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Government ID file is required'
                    }, status=400)
                    
            elif verification_type == 'selfie':
                if 'selfie' in request.FILES:
                    selfie = request.FILES['selfie']
                    # Validate file type
                    if not selfie.content_type.startswith('image/'):
                        return JsonResponse({
                            'status': 'error',
                            'message': 'Please upload a valid image file'
                        }, status=400)
                    
                    verification_request.selfie = selfie
                    verification_request.status = 'completed'
                    verification_request.acceptance_status = 'pending'
                    verification_request.save()
                    logger.info(f"Saved selfie file for verification request {verification_request.id}")
                else:
                    logger.error("Selfie file not provided")
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Selfie file is required'
                    }, status=400)
            
            # Create a message in the chat
            ChatMessage.objects.create(
                chat_room=chat_room,
                sender=request.user,
                message=f'Submitted {verification_type.replace("_", " ")} verification',
                message_type='verification_submitted'
            )
            logger.info(f"Created chat message for verification submission {verification_request.id}")
            
            return JsonResponse({
                'status': 'success',
                'message': f'{verification_type.title()} submitted successfully'
            })
            
        except Exception as e:
            logger.error(f"Error handling verification submission: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
            
    except Exception as e:
        logger.error(f"Unexpected error in submit_verification: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
@require_POST
@ensure_csrf_cookie
def set_rental_terms(request):
    try:
        logger.info(f"Received rental terms request from user {request.user.username}")
        
        try:
            data = json.loads(request.body)
            chat_room_id = data.get('chat_room_id')
            
            if not chat_room_id:
                logger.error("Missing chat_room_id in request")
                return JsonResponse({
                    'status': 'error',
                    'message': 'Missing chat_room_id'
                }, status=400)
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid JSON data'
            }, status=400)
        
        try:
            chat_room = get_object_or_404(ChatRoom, id=chat_room_id)
        except Exception as e:
            logger.error(f"Error getting chat room {chat_room_id}: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': 'Chat room not found'
            }, status=404)
        
        # Check if user is the lender
        if request.user != chat_room.order.product.user:
            logger.warning(f"User {request.user.username} attempted to set rental terms but is not the lender")
            return JsonResponse({
                'status': 'error',
                'message': 'Only lenders can set rental terms'
            }, status=403)
            
        required_fields = ['start_date', 'end_date', 'rental_price', 'security_deposit']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            logger.error(f"Missing rental terms fields: {', '.join(missing_fields)}")
            return JsonResponse({
                'status': 'error',
                'message': f'Missing required fields: {", ".join(missing_fields)}'
            }, status=400)
            
        # Create a message with rental terms
        try:
            # Update the order with rental terms
            order = chat_room.order
            order.start_date = data.get('start_date')
            order.end_date = data.get('end_date')
            order.rental_price = data.get('rental_price')
            order.security_deposit = data.get('security_deposit')
            order.late_fees = data.get('late_fees', 0)
            order.damage_penalties = data.get('damage_penalties', '')
            order.save()
            
            # Create a message to notify about the rental terms
            message_text = (
                f"Rental Terms Set:\n"
                f"Start Date: {data.get('start_date')}\n"
                f"End Date: {data.get('end_date')}\n"
                f"Rental Price: ${data.get('rental_price')}\n"
                f"Security Deposit: ${data.get('security_deposit')}"
            )
            if data.get('late_fees'):
                message_text += f"\nLate Fees: ${data.get('late_fees')}"
            if data.get('damage_penalties'):
                message_text += f"\nDamage Penalties: {data.get('damage_penalties')}"
            
            ChatMessage.objects.create(
                chat_room=chat_room,
                sender=request.user,
                message=message_text,
                message_type='rental_terms'
            )
            logger.info(f"Created chat message for rental terms in chat room {chat_room_id}")
            
            return JsonResponse({'status': 'success'})
            
        except Exception as e:
            logger.error(f"Error creating rental terms message: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': 'Error setting rental terms'
            }, status=500)
            
    except Exception as e:
        logger.error(f"Unexpected error in set_rental_terms: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
@require_POST
@ensure_csrf_cookie
def delete_verification(request):
    try:
        data = json.loads(request.body)
        verification_id = data.get('verification_id')
        
        if not verification_id:
            return JsonResponse({
                'status': 'error',
                'message': 'Verification ID is required'
            }, status=400)
        
        try:
            verification = VerificationRequest.objects.get(id=verification_id)
        except VerificationRequest.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Verification request not found'
            }, status=404)
        
        # Check if user is the lender
        if request.user != verification.chat_room.order.product.user:
            return JsonResponse({
                'status': 'error',
                'message': 'Only lenders can delete verification requests'
            }, status=403)
        
        # Delete associated files
        if verification.id_document:
            verification.id_document.delete()
        if verification.selfie:
            verification.selfie.delete()
        
        # Delete the verification request
        verification.delete()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Verification request deleted successfully'
        })
        
    except Exception as e:
        logger.error(f"Error deleting verification: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500) 