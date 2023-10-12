f = CurrentFont()
ORDINALS = ['1ST', '2ND', '3RD'] + [f'{i}TH' for i in range(4, 10)]

for i in range(1, 9):
    cmp_1 = 'f.liga'
    cmp_2 = 'dotlessi.liga'
    g_1 = f[cmp_1]
    g_2 = f[cmp_2]
    liga_name = '_'.join(['f'] + i * ['i'])
    g = f.newGlyph(liga_name, clear=True)
    x_offset = 0
    g.appendComponent(cmp_1)
    for anchor in f['f'].anchors:
        anchor_name = anchor.name + ORDINALS[0]
        g.appendAnchor(anchor_name, anchor.position)
    x_offset += g_1.width
    for j in range(i):
        g.appendComponent(cmp_2, (x_offset, 0))
        for anchor in f['dotlessi'].anchors:
            anchor_name = anchor.name + ORDINALS[j + 1]
            g.appendAnchor(anchor_name, (anchor.x + x_offset, anchor.y))
        x_offset += g_2.width
    g.rightMargin = g_2.rightMargin
    g.changed()

# add a random anchor to the last ligature, so the mark feature writer finds
# something to complain about:
g.appendAnchor('randomAnchor3RD', (100, 100))
