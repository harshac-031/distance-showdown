import streamlit as st
import folium
from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation
import reverse_geocoder
import geonamescache

st.title("Where Am I? Be a Location Detective")
st.write("Your computer can find where you are right now as two numbers: **latitude** and **longitude**. "
         "Can you guess the nearest city, the state and the country that those two numbers point to?")

# Step 1: real cities and countries (offline)
gc = geonamescache.GeonamesCache()
countries = gc.get_countries()
cities = [c for c in gc.get_cities().values() if c["population"] >= 500_000]

# Step 2: find where you are (the button asks your browser for permission)
st.subheader("Step 1: Find where you are")
st.write("Press the small target button below and allow your browser to share your location. No GPS? Use the two sliders instead.")
gps = streamlit_geolocation()
lat = st.slider("Latitude (moves you North / South)", -90.0, 90.0, 0.0)
lon = st.slider("Longitude (moves you East / West)", -180.0, 180.0, 0.0)
if gps["latitude"] is not None:
    lat, lon = gps["latitude"], gps["longitude"]           # the real location wins over the sliders
first, second = st.columns(2)
first.metric("Your latitude", f"{lat:.2f}")
second.metric("Your longitude", f"{lon:.2f}")
st.caption("This app does not save your location.")

# Step 3: the computer works out the answers (you can't see them yet!)
def gap(city):
    return (city["latitude"] - lat) ** 2 + (city["longitude"] - lon) ** 2

nearby = sorted(cities, key=gap)[:5]                       # the 5 closest big cities
around = [(lat + up, lon + side) for up in (-5, 0, 5) for side in (-5, 0, 5)]     # 9 spots: you and 8 spots around you
places = reverse_geocoder.search(around, mode=1)           # (the middle spot is you, so places[4] is you)
answer_city = nearby[0]["name"]
answer_state = places[4]["admin1"] or "No state here"
answer_country = countries.get(places[4]["cc"], {}).get("name", places[4]["cc"])

# Step 4: the student guesses
st.subheader("Step 2: Make your guesses")
city_guess = st.selectbox("Which big city is NEAREST to you?", sorted({city["name"] for city in nearby}), index=None, placeholder="Choose a city")
state_guess = st.selectbox("Which state or region are you in?", sorted({place["admin1"] or "No state here" for place in places}), index=None, placeholder="Choose a state or region")
country_guess = st.selectbox("Which country are you in?", sorted(country["name"] for country in countries.values()), index=None, placeholder="Choose a country")
if None in (city_guess, state_guess, country_guess):
    st.stop()                                              # wait until all 3 guesses are made

# Step 5: reveal the answers
st.subheader("Step 3: The answers")
score = 0
for label, guess, answer in [("Nearest big city", city_guess, answer_city), ("State or region", state_guess, answer_state),
                             ("Country", country_guess, answer_country)]:
    if guess == answer:
        st.success(f"{label}: {answer}. Right!")
        score = score + 1
    else:
        st.error(f"{label}: it is {answer}, not {guess}.")
st.write(f"You got **{score} out of 3** right.")

# Step 6: you and your nearest city on the map
m = folium.Map(min_zoom=2, max_bounds=True, tiles=None)                     # one world only, no repeats
folium.TileLayer("Esri.WorldImagery", no_wrap=True, bounds=[[-90, -180], [90, 180]]).add_to(m)
folium.Marker([lat, lon], icon=folium.Icon(color="red", icon="user", prefix="fa"), tooltip="You are here").add_to(m)
folium.CircleMarker([nearby[0]["latitude"], nearby[0]["longitude"]], radius=8, color="yellow", fill=True,
                    tooltip=folium.Tooltip(answer_city, permanent=True)).add_to(m)
folium.PolyLine([[lat, lon], [nearby[0]["latitude"], nearby[0]["longitude"]]], color="yellow").add_to(m)
m.fit_bounds(m.get_bounds(), max_zoom=10)
st_folium(m, width=700, height=350, returned_objects=[])
