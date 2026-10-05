import math
import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
import geonamescache

st.title("Distance Showdown: Round Earth vs Flat Map")
st.write("The Earth is round, but paper maps are flat. So a flat map can give the WRONG distance! "
         "Pick your home city and two other cities. Which one is closer? Then see what a flat map would guess.")

# Step 1: load real cities (offline). The biggest city wins when two share a name.
gc = geonamescache.GeonamesCache()
big = [c for c in gc.get_cities().values() if c["population"] >= 1_000_000]
cities = {c["name"]: c for c in sorted(big, key=lambda c: c["population"])}
names = sorted(cities)

# Step 2: two ways to measure the distance between city a and city b
def real_distance(a, b):                 # ready-made formula for a ROUND Earth (km)
    p1, p2 = math.radians(a["latitude"]), math.radians(b["latitude"])
    x = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(b["longitude"] - a["longitude"]) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(x))

def flat_map_distance(a, b):             # a flat-map guess: treat the Earth like a sheet of paper (1 degree is about 111 km)
    return math.hypot(a["latitude"] - b["latitude"], a["longitude"] - b["longitude"]) * 111

def curved_path(a, b):                   # ready-made helper: points along the shortest path on the globe
    p1, l1, p2, l2 = (math.radians(v) for v in (a["latitude"], a["longitude"], b["latitude"], b["longitude"]))
    angle = real_distance(a, b) / 6371
    path, last = [], a["longitude"]
    for i in range(41):
        f = i / 40
        u, v = math.sin((1 - f) * angle) / math.sin(angle), math.sin(f * angle) / math.sin(angle)
        x = u * math.cos(p1) * math.cos(l1) + v * math.cos(p2) * math.cos(l2)
        y = u * math.cos(p1) * math.sin(l1) + v * math.cos(p2) * math.sin(l2)
        z = u * math.sin(p1) + v * math.sin(p2)
        lon = math.degrees(math.atan2(y, x))
        lon += 360 * round((last - lon) / 360)           # do not jump across the map edge
        path.append([math.degrees(math.atan2(z, math.hypot(x, y))), lon])
        last = lon
    return path

# Step 3: the student chooses three cities
home_name = st.selectbox("Your home city (pick the big city nearest to you)", names, index=names.index("London"))
left, right = st.columns(2)
name1 = left.selectbox("City 1", names, index=names.index("Cairo"))
name2 = right.selectbox("City 2", names, index=names.index("New York City"))
guess = st.radio(f"Which one is closer to {home_name}?", [name1, name2], index=None)

# Step 4: reveal the answer
if guess and len({home_name, name1, name2}) == 3:
    home, c1, c2 = cities[home_name], cities[name1], cities[name2]
    real_winner = name1 if real_distance(home, c1) < real_distance(home, c2) else name2
    flat_winner = name1 if flat_map_distance(home, c1) < flat_map_distance(home, c2) else name2

    if guess == real_winner:
        st.success(f"Correct! {real_winner} is closer.")
    else:
        st.error(f"Not quite. {real_winner} is closer.")
    if flat_winner != real_winner:
        st.balloons()
        st.warning(f"The flat map got it WRONG! It says {flat_winner} is closer, but on the real round Earth "
                   f"{real_winner} is closer. Flat maps stretch the far North and South.")
    else:
        st.info("The flat map got it right this time. Try other cities: can you find a pair where the flat map is WRONG?")

    # Step 5: distance bars (green = real, red = flat-map guess), next to the satellite map
    bars = pd.DataFrame([{"City": n, "Measure": m, "Distance (km)": round(f(home, cities[n]))}
                         for n in (name1, name2)
                         for m, f in (("Real distance", real_distance), ("Flat-map guess", flat_map_distance))])
    chart_box, map_box = st.columns(2)
    chart = px.bar(bars, x="City", y="Distance (km)", color="Measure", barmode="group", text_auto=True,
                   color_discrete_map={"Real distance": "#2ecc71", "Flat-map guess": "#e74c3c"},
                   title=f"How far is each city from {home_name}?")
    chart.update_layout(height=450, legend_title_text="")
    chart_box.plotly_chart(chart)

    # Step 6: satellite map. The shortest path is a CURVE, not a straight line!
    m = folium.Map(tiles="Esri.WorldImagery")
    points = [[home["latitude"], home["longitude"]]]
    for c, colour in ((c1, "yellow"), (c2, "cyan")):
        path = curved_path(home, c)
        folium.PolyLine(path, color=colour, weight=4, tooltip=f"{c['name']}: {real_distance(home, c):,.0f} km").add_to(m)
        folium.CircleMarker(path[-1], radius=7, color=colour, fill=True,
                            tooltip=folium.Tooltip(c["name"], permanent=True)).add_to(m)
        points += path
    folium.Marker(points[0], icon=folium.Icon(color="red", icon="home"), tooltip=folium.Tooltip(home_name, permanent=True)).add_to(m)
    m.fit_bounds([[min(p[0] for p in points), min(p[1] for p in points)],
                  [max(p[0] for p in points), max(p[1] for p in points)]])
    with map_box:
        st_folium(m, height=450, returned_objects=[])
