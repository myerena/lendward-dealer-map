"""Folium presentation: one marker per entry, expandable shared-ZIP clusters."""

import html

import folium
from branca.element import MacroElement, Template
from folium.plugins import MarkerCluster


class ExpandSharedZip(MacroElement):
    """One click fans out markers at the same point, at any zoom level."""

    _template = Template("""
    {% macro script(this, kwargs) %}
    {{ this._parent.get_name() }}.on('clusterclick', function(event) {
        const markers = event.layer.getAllChildMarkers();
        const first = markers[0].getLatLng();
        if (markers.every(marker => marker.getLatLng().equals(first))) {
            event.layer.spiderfy();
        } else {
            event.layer.zoomToBounds({padding: [35, 35]});
        }
    });
    {% endmacro %}
    """)


def popup_html(dealer):
    def safe(key):
        # Folium uses JavaScript template literals internally as well as HTML.
        return html.escape(str(dealer.get(key, "")), quote=True).replace("`", "&#96;").replace("$", "&#36;")

    review = f'<p style="color:#975b0b">Review: {safe("review_note")}</p>' if dealer["review_note"] else ""
    key = f'<p style="font-size:11px;color:#667085">Source group: {safe("dealer_key")}</p>' if review else ""
    return f"""<div style="font:14px/1.5 system-ui;min-width:210px;max-width:310px">
        <strong style="font-size:17px;color:#153a52">{safe('dealer_name')}</strong>
        <p>{safe('postal_city')}, {safe('state')} {safe('zip')}</p>
        <p><b>{safe('campaign_count')}</b> campaigns in this report<br>
        Latest drop: {safe('latest_drop_date') or 'Not provided'}</p>
        {review}{key}<small style="color:#667085">Approximate ZIP location</small></div>"""


def build_map(dealers, place=None):
    center = [place["latitude"], place["longitude"]] if place else [38.8, -97.5]
    map_object = folium.Map(
        location=center, zoom_start=10 if place else 4, tiles=None,
        control_scale=True, prefer_canvas=True,
    )
    folium.TileLayer(
        tiles="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        name="Street map", max_zoom=19,
    ).add_to(map_object)
    clusters = MarkerCluster(
        show_coverage_on_hover=False, zoom_to_bounds_on_click=False,
        spiderfy_on_max_zoom=True, max_cluster_radius=38,
        icon_create_function="""function(cluster) {
            return L.divIcon({html: '<div style="background:#153a52;color:white;border:4px solid #c8dce7;border-radius:50%;width:42px;height:42px;display:flex;align-items:center;justify-content:center;font:600 14px system-ui;box-sizing:border-box">' + cluster.getChildCount() + '</div>', className:'dealer-cluster', iconSize:[42,42]});
        }""",
    ).add_to(map_object)
    ExpandSharedZip().add_to(clusters)
    for dealer in dealers:
        if dealer["latitude"] is None:
            continue
        color = "#b57516" if dealer["review_note"] else "#16798b"
        icon = folium.DivIcon(
            html=f'<div style="width:23px;height:23px;background:{color};border:3px solid white;border-radius:50% 50% 50% 0;transform:rotate(-45deg);box-shadow:0 2px 5px #0005"></div>',
            icon_size=(26, 30), icon_anchor=(13, 30),
        )
        folium.Marker(
            [dealer["latitude"], dealer["longitude"]], icon=icon,
            title=dealer["dealer_name"], alt=dealer["dealer_name"],
            popup=folium.Popup(popup_html(dealer), max_width=340),
            tooltip=html.escape(dealer["dealer_name"]).replace("`", "&#96;").replace("$", "&#36;"),
        ).add_to(clusters)
    if place:
        folium.CircleMarker(center, radius=5, color="#153a52", weight=2,
                            fill=True, fill_color="white", fill_opacity=1,
                            tooltip="Searched location").add_to(map_object)
    return map_object
