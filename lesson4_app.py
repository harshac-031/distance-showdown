import math
import streamlit as st
import plotly.graph_objects as go
import geonamescache

st.title("Distance Showdown: Fool the Flat Ruler!")
st.write("Pick your home city and two other cities. Which one is closer? "
         "Then try to find a pair that FOOLS a flat-map ruler!")

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

def flat_distance(a, b):                 # the "flat map ruler" (1 degree is about 111 km)
    return math.hypot(a["latitude"] - b["latitude"], a["longitude"] - b["longitude"]) * 111

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
    flat_winner = name1 if flat_distance(home, c1) < flat_distance(home, c2) else name2

    if guess == real_winner:
        st.success(f"Correct! {real_winner} is closer.")
    else:
        st.error(f"Not quite. {real_winner} is closer.")
    for name in (name1, name2):
        st.write(f"**{name}**: real distance {real_distance(home, cities[name]):,.0f} km, "
                 f"flat ruler says {flat_distance(home, cities[name]):,.0f} km")
    if flat_winner != real_winner:
        st.balloons()
        st.warning(f"You FOOLED the flat ruler! It picked {flat_winner}. Flat maps stretch the far North and South.")
    else:
        st.info("The flat ruler got it right this time. Can you find a pair that fools it?")

    # Step 5: on a globe, the shortest path is a curve
    fig = go.Figure()
    for name in (name1, name2):
        fig.add_trace(go.Scattergeo(lat=[home["latitude"], cities[name]["latitude"]],
                                    lon=[home["longitude"], cities[name]["longitude"]],
                                    text=[home_name, name], mode="lines+markers+text", line=dict(width=3)))
    fig.update_geos(projection_type="natural earth", showland=True, showocean=True,
                    landcolor="#7aa65a", oceancolor="#2a6f97")
    fig.update_layout(height=400, margin=dict(l=0, r=0, t=0, b=0), showlegend=False)
    st.plotly_chart(fig)
