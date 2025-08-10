import streamlit as st

# Define the pages
main_page = st.Page(
    "pages/homepage.py", title="Nouveau formulaire", icon=":material/edit_document:")

ma_bibliotheque = st.Page(
    "pages/my_library.py", title="Ma bibliothèque", icon=":material/newsstand:")

user_guide = st.Page(
    "pages/user_guide.py", title="Guide d'utilisation", icon=":material/info:")

# Set up navigation
pg = st.navigation([main_page, ma_bibliotheque, user_guide])

# Run the selected page
pg.run()
