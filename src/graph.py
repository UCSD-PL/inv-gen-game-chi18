def strongly_connected_components(graph):
    """
    Tarjan's Algorithm (named for its discoverer, Robert Tarjan) is a graph
    theory algorithm for finding the strongly connected components of a graph.

    Based on:
    http://en.wikipedia.org/wiki/Tarjan%27s_strongly_connected_components_algorithm
    Taken from: http://www.logarithmic.net/pfh-files/blog/01208083168/tarjan.py
    Credit to: Dries Verdegem
    """

    index_counter = [0]
    stack = []
    lowlinks = {}
    index = {}
    result = []

    def strongconnect(node):
        # set the depth index for this node to the smallest unused index
        index[node] = index_counter[0]
        lowlinks[node] = index_counter[0]
        index_counter[0] += 1
        stack.append(node)

        # Consider successors of `node`
        try:
            successors = graph[node]
        except Exception:
            successors = []
        for successor in successors:
            if successor not in lowlinks:
                # Successor has not yet been visited; recurse on it
                strongconnect(successor)
                lowlinks[node] = min(lowlinks[node],lowlinks[successor])
            elif successor in stack:
                # the successor is in the stack and hence in the current
                # strongly connected component (SCC)
                lowlinks[node] = min(lowlinks[node],index[successor])

        # If `node` is a root node, pop the stack and generate an SCC
        if lowlinks[node] == index[node]:
            connected_component = []

            while True:
                successor = stack.pop()
                connected_component.append(successor)
                if successor == node:
                    break
            component = tuple(connected_component)
            # storing the result
            result.append(component)

    for node in graph:
        if node not in lowlinks:
            strongconnect(node)

    return result

def collapse_scc(g, ccs):
    # TODO: Assert ccs is a partitioning of g's edges
    cc_i = { x : ind for (ind, comp) in enumerate(ccs) for x in comp }
    g1 = { i : set([]) for i in xrange(len(ccs)) }
    for n in g:
        for n1 in g[n]:
            if (cc_i[n] != cc_i[n1]):
                g1[cc_i[n]].add(cc_i[n1])
    return g1

def topo_sort(g):
    rev_g = { n : set() for n in g.keys() }

    for n in g:
        for n1 in g[n]:
            rev_g[n1].add(n)

    roots = set([ n for n in g.keys() if len(g[n]) == 0 ])
    wl = [ x for x in roots ]
    ind = 0
    order = { n : 0 for n in g.keys() }
    cnt = { n : (1 if n in roots else 0) for n in g.keys() }

    while (len(wl) > 0):
        # INV: cnt[n] == # times n appears in wl
        n = wl.pop(0);
        cnt[n] -= 1

        # As an optimization, only interested in the LAST occurrance of n on
        # the wl
        if (cnt[n] > 0):
            continue

        order[n] = max(ind, order[n])
        ind += 1;
        for n1 in rev_g[n]:
            cnt[n1] += 1
            wl.append(n1)

    # Assert that order is a valid ordering of the nodes in g
    assert (sorted(list(order.values())) == list(range(0, len(g))))
    assert (sorted(list(order.keys())) == sorted(list(g.keys())))
    # Assert that this IS a topological sort
    for n in g:
        for n1 in g[n]:
            assert order[n] > order[n1]

    return [ order[i] for i in xrange(len(g)) ]
