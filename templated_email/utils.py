
# From http://stackoverflow.com/questions/2687173/django-how-can-i-get-a-block-from-a-template
from django.template import Context
from django.template.loader_tags import BlockNode, ExtendsNode
try:
    xrange
except NameError:  # Python 3
    xrange = range

node_parent_cache = {}


class BlockNotFound(Exception):
    pass


def get_node_parent(template_name, node, context):
    """
    Cache lookups for the parent node (the {% extends "..." %}).  In 1.9 the template will
    be re-evaluated each time the node is hit (? no idea why). This wouldn't be an issue,
    the second time the template loader can't find the file (why, did it lose the dirs?)

     This is commonly a problem because of the call in vanilla_django where it extracts the
     individual blocks.
       for part in ['subject', 'html', ...]:
    """
    global node_parent_cache
    parent = node_parent_cache.get(template_name, None)
    if not parent:
        parent = node_parent_cache[template_name] = node.get_parent(context)
    return parent


def _iter_nodes(template, context, name, block_lookups):
    for node in template:
        if isinstance(node, BlockNode) and node.name == name:
            # Rudimentary handling of extended templates, for issue #3
            for i in xrange(len(node.nodelist)):
                n = node.nodelist[i]
                if isinstance(n, BlockNode) and n.name in block_lookups:
                    node.nodelist[i] = block_lookups[n.name]
            return node.render(context)
        elif isinstance(node, ExtendsNode):
            # {% extends "email/my_base.email" %} or similar, e.g. this is a derived template
            lookups = dict([(n.name, n) for n in node.nodelist if isinstance(n, BlockNode)])
            lookups.update(block_lookups)
            parent = get_node_parent(template.name, node, context)
            return _get_node(parent, context, name, lookups)

    raise BlockNotFound("Node '%s' could not be found in template." % name)


def _get_node(template, context=Context(), name='subject', block_lookups=None):
    if block_lookups is None:
        block_lookups = {}

    try:
        return _iter_nodes(template, context, name, block_lookups)
    except TypeError:
        # this is expected if `for node in template` failes.  this means the template is of type
        # django.templates.backends.django.Template, so get the inner template which is the proper one
        context.template = template.template
        return _iter_nodes(template.template, context, name, block_lookups)
