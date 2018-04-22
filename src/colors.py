
colors = ["black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"]

def make_colors(start):
    res = {}
    for i in range(len(colors)):
        res[colors[i]] = '\033[' + str(start+i) + 'm'
    return res

foreground_normal = make_colors(30)
foreground_bright = make_colors(90)

def color(s, c, scheme = None):
    if (scheme == None):
        scheme = foreground_bright
    return scheme[c] + s + '\033[0m'

def bold(s):
    return '\033[1m' + s + '\033[0m'

