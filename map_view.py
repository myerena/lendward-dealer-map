"""Folium presentation: one marker per entry, expandable shared-ZIP clusters."""

import html
import math

import folium
from branca.element import MacroElement, Template
from folium.plugins import MarkerCluster


class ClusterInteractions(MacroElement):
    """List grouped stores on hover and expand their pins on click."""

    _template = Template("""
    {% macro script(this, kwargs) %}
    {{ this._parent.get_name() }}.on('clusterclick', function(event) {
        event.layer.closeTooltip();
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


class DealerMarkers(MacroElement):
    """Render all markers in one loop instead of hundreds of template trees."""

    _template = Template("""
    {% macro script(this, kwargs) %}
    {{ this.markers | tojson }}.forEach(function(dealer) {
        const icon = L.divIcon({
            html: '<div style="width:23px;height:23px;background:' + dealer.color + ';border:3px solid white;border-radius:50% 50% 50% 0;transform:rotate(-45deg);box-shadow:0 2px 5px #0005"></div>',
            iconSize: [26, 30], iconAnchor: [13, 30], className: 'dealer-pin'
        });
        L.marker(dealer.location, {icon: icon, title: dealer.name, alt: dealer.name})
            .bindPopup(dealer.popup, {maxWidth: 340})
            .bindTooltip(dealer.tooltip)
            .addTo({{ this._parent.get_name() }});
    });
    {% endmacro %}
    """)

    def __init__(self, dealers):
        super().__init__()
        self.markers = [
            {"location": [d["latitude"], d["longitude"]], "name": d["dealer_name"],
             "color": "#b57516" if d["review_note"] else "#16798b",
             "popup": popup_html(d), "tooltip": html.escape(d["dealer_name"])}
            for d in dealers if d["latitude"] is not None
        ]


def search_overlay(place, radius):
    """A replaceable search layer; dealer markers remain on the base map."""
    overlay = folium.FeatureGroup(name="Searched area")
    if not place:
        return overlay
    center = [place["latitude"], place["longitude"]]
    for miles, color in [(50, "#7457a6"), (25, "#16798b"), (10, "#153a52")]:
        if miles <= radius:
            folium.Circle(center, radius=miles * 1609.344, color=color, weight=2,
                          fill=False).add_to(overlay)
            folium.Marker(
                [center[0] + math.degrees(miles * 1609.344 / 6371000), center[1]],
                icon=folium.DivIcon(html=f'<div style="background:white;border:1px solid {color};color:{color};border-radius:4px;text-align:center;font:600 12px/22px system-ui">{miles} mi</div>',
                                    icon_size=(48, 24), icon_anchor=(24, 12)),
                interactive=False,
            ).add_to(overlay)
    folium.CircleMarker(center, radius=5, color="#153a52", weight=2,
                        fill=True, fill_color="white", fill_opacity=1).add_to(overlay)
    # Folium's path_options drops interactive/pane kwargs, so set them explicitly.
    for layer in overlay._children.values():
        layer.options.update(pane="distance-rings", interactive=False, keyboard=False)
    return overlay


def build_map(dealers):
    map_object = folium.Map(
        location=[38.8, -97.5], zoom_start=4, tiles=None,
        control_scale=True, prefer_canvas=True,
    )
    folium.map.CustomPane("distance-rings", z_index=450, pointer_events=False).add_to(map_object)
    folium.TileLayer(
        tiles="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        name="Street map", max_zoom=19,
    ).add_to(map_object)
    clusters = MarkerCluster(
        show_coverage_on_hover=False, zoom_to_bounds_on_click=False,
        spiderfy_on_max_zoom=True, max_cluster_radius=38,
        icon_create_function="""function(cluster) {
            // MarkerCluster uses itself as its icon and needs an explicit anchor.
            cluster.options.tooltipAnchor = [0, 0];
            const stores = cluster.getAllChildMarkers().slice().sort((a, b) =>
                a.options.title.localeCompare(b.options.title));
            const content = document.createElement('div');
            content.style.cssText = 'width:300px;max-width:65vw;max-height:240px;overflow-y:auto;white-space:normal;font:13px/1.5 system-ui';
            const heading = document.createElement('strong');
            heading.textContent = stores.length + ' stores';
            content.appendChild(heading);
            const list = document.createElement('ul');
            list.style.cssText = 'margin:6px 0 0;padding-left:18px';
            stores.forEach(marker => {
                const item = document.createElement('li');
                item.textContent = marker.options.title;
                list.appendChild(item);
            });
            content.appendChild(list);
            cluster.unbindTooltip();
            cluster.bindTooltip(content, {direction:'auto', opacity:1, interactive:true});
            return L.divIcon({html: '<div style="background:#153a52;color:white;border:4px solid #c8dce7;border-radius:50%;width:42px;height:42px;display:flex;align-items:center;justify-content:center;font:600 14px system-ui;box-sizing:border-box">' + cluster.getChildCount() + '</div>', className:'dealer-cluster', iconSize:[42,42]});
        }""",
    ).add_to(map_object)
    ClusterInteractions().add_to(clusters)
    DealerMarkers(dealers).add_to(clusters)
    return map_object
