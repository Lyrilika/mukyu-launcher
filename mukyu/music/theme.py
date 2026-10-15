import colorsys

PALETTE_KEYS = (
    'mu_primary', 'mu_on_primary', 'mu_primary_container', 'mu_on_primary_container',
    'mu_secondary_container', 'mu_surface', 'mu_surface_container', 'mu_surface_high',
    'mu_text', 'mu_text_dim', 'mu_track',
)


def dominant_rgb(pixels, width, height, channels, rowstride, bins=12):
    weight = [0.0] * bins
    sums = [[0.0, 0.0, 0.0] for _ in range(bins)]
    total_r = total_g = total_b = 0.0
    count = 0
    for y in range(height):
        base = y * rowstride
        for x in range(width):
            i = base + x * channels
            r, g, b = pixels[i], pixels[i + 1], pixels[i + 2]
            total_r += r
            total_g += g
            total_b += b
            count += 1
            h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
            w = (s * s + 0.02) * max(0.04, 1.0 - abs(2.0 * l - 1.0)) ** 1.5
            k = min(bins - 1, int(h * bins))
            weight[k] += w
            sums[k][0] += r * w
            sums[k][1] += g * w
            sums[k][2] += b * w
    if count == 0:
        return (110, 110, 140)
    best = max(range(bins), key=lambda k: weight[k])
    if weight[best] <= 0.0:
        return (round(total_r / count), round(total_g / count), round(total_b / count))
    w = weight[best]
    return (round(sums[best][0] / w), round(sums[best][1] / w), round(sums[best][2] / w))


def _hex(h, s, l):
    r, g, b = colorsys.hls_to_rgb(h % 1.0, max(0.0, min(1.0, l)), max(0.0, min(1.0, s)))
    return '#%02x%02x%02x' % (round(r * 255), round(g * 255), round(b * 255))


def _luminance(hex_color):
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def _contrast(a, b):
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def make_palette(r, g, b, mode='dark'):
    h, _l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    accent = 0.10 if s < 0.12 else max(0.38, min(s, 0.85))
    if mode == 'light':
        on_primary = _hex(h, accent * 0.3, 0.98)
        lightness = 0.38
        while lightness > 0.2 and _contrast(on_primary, _hex(h, accent, lightness)) < 4.5:
            lightness -= 0.02
        return {
            'mu_primary':              _hex(h, accent,        lightness),
            'mu_on_primary':           on_primary,
            'mu_primary_container':    _hex(h, accent * 0.85, 0.86),
            'mu_on_primary_container': _hex(h, accent,        0.17),
            'mu_secondary_container':  _hex(h, accent * 0.60, 0.89),
            'mu_surface':              _hex(h, accent * 0.60, 0.955),
            'mu_surface_container':    _hex(h, accent * 0.55, 0.925),
            'mu_surface_high':         _hex(h, accent * 0.55, 0.895),
            'mu_text':                 _hex(h, accent * 0.45, 0.11),
            'mu_text_dim':             _hex(h, accent * 0.25, 0.36),
            'mu_track':                _hex(h, accent * 0.40, 0.77),
        }
    return {
        'mu_primary':              _hex(h, accent,        0.77),
        'mu_on_primary':           _hex(h, accent * 0.7,  0.13),
        'mu_primary_container':    _hex(h, accent * 0.55, 0.30),
        'mu_on_primary_container': _hex(h, accent,        0.90),
        'mu_secondary_container':  _hex(h, accent * 0.38, 0.27),
        'mu_surface':              _hex(h, accent * 0.45, 0.095),
        'mu_surface_container':    _hex(h, accent * 0.42, 0.150),
        'mu_surface_high':         _hex(h, accent * 0.40, 0.210),
        'mu_text':                 _hex(h, accent * 0.20, 0.94),
        'mu_text_dim':             _hex(h, accent * 0.16, 0.72),
        'mu_track':                _hex(h, accent * 0.30, 0.31),
    }


def palette_from_hue(hue, mode='dark'):
    r, g, b = colorsys.hls_to_rgb(hue % 1.0, 0.55, 0.6)
    return make_palette(round(r * 255), round(g * 255), round(b * 255), mode)


def palette_css(palette):
    return ''.join(f'@define-color {name} {value};\n' for name, value in palette.items())
