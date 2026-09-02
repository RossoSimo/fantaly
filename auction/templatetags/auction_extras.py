from django import template

register = template.Library()


@register.filter
def dictitem(mapping, key):
    """Look up `key` in `mapping`. Django templates can't do dict[var]
    with a dynamic key, so this fills that gap for e.g. budgets|dictitem:manager.pk."""
    if mapping is None:
        return None
    return mapping.get(key)
