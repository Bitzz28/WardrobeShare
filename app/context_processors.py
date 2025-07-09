from .models import Post, Order

def user_counts(request):
    """Add user-related counts to template context."""
    if request.user.is_authenticated:
        return {
            'user_posts_count': Post.objects.filter(user=request.user).count(),
            'user_orders_count': Order.objects.filter(user=request.user, order_status=True).count(),
        }
    return {} 