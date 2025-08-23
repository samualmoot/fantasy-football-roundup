"""
Custom template filters for dictionary operations.
"""

from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Template filter to get a dictionary value by key.
    Usage: {{ dictionary|get_item:key }}
    """
    if dictionary and key in dictionary:
        return dictionary[key]
    return None
