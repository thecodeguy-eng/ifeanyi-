from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Return the value of a dictionary for the given key."""
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.filter
def unique_users(activities):
    """
    Return the count of unique users from a list or queryset of activities.
    Each activity is assumed to have a 'user' field.
    """
    if not activities:
        return 0
    return len(set(a.user for a in activities))

@register.filter(name='format_action')
def format_action(value):
    """
    Format action type by replacing underscores with spaces and title casing
    Usage: {{ action_type|format_action }}
    Example: "PAGE_VIEW" becomes "Page View"
    """
    if not value:
        return value
    
    # Replace underscores with spaces and convert to title case
    return str(value).replace('_', ' ').title()


@register.filter(name='replace')
def replace(value, args):
    """
    Replaces old with new in value
    Usage: {{ value|replace:"old,new" }}
    Example: {{ "hello_world"|replace:"_," " }} becomes "hello world"
    """
    if not args or ',' not in args:
        return value
    
    old, new = args.split(',', 1)
    return str(value).replace(old, new)