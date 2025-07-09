from django import template

register = template.Library()

@register.filter
def filter_borrowing(chats, user):
    """Filter chat rooms where the user is the borrower"""
    return [chat for chat in chats if chat.order.user == user]

@register.filter
def filter_lending(chats, user):
    """Filter chat rooms where the user is the lender"""
    return [chat for chat in chats if chat.order.product.user == user] 