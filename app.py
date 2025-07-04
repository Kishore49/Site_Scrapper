import requests
from bs4 import BeautifulSoup
import pandas as pd
import streamlit as st
import re

st.set_page_config(page_title="📚 Advanced Book Scraper", layout="wide")
st.title("📚 Books to Scrape - Web Scraper")
st.markdown("Scrape book data with advanced filtering from [Books to Scrape](http://books.toscrape.com).")

pages = st.number_input("🔢 How many pages to scrape?", min_value=1, max_value=50, value=1, step=1)

RATING_MAP = {
    "One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5
}

def extract_price_value(price_str):
    return float(re.findall(r'[\d.]+', price_str)[0])

@st.cache_data(show_spinner=True)
def scrape_books(pages):
    all_books = []
    base_url = "http://books.toscrape.com/catalogue/page-{}.html"
    main_url = "http://books.toscrape.com/"

    for page in range(1, pages + 1):
        url = base_url.format(page)
        res = requests.get(url)
        soup = BeautifulSoup(res.text, "html.parser")
        books = soup.find_all("article", class_="product_pod")
        for book in books:
            title = book.h3.a['title']
            price = book.find("p", class_="price_color").text
            availability = book.find("p", class_="instock availability").text.strip()
            rating_class = book.p['class'][1]
            rating = RATING_MAP.get(rating_class, 0)
            img_tag = book.find("img")
            img_url = main_url + img_tag['src'].replace("../", "")
            detail_link = book.h3.a['href']
            detail_url = main_url + "catalogue/" + detail_link
            detail_res = requests.get(detail_url)
            detail_soup = BeautifulSoup(detail_res.text, "html.parser")
            breadcrumb = detail_soup.select("ul.breadcrumb li a")
            category = breadcrumb[2].text.strip() if len(breadcrumb) > 2 else "Unknown"
            product_table = detail_soup.find("table", class_="table table-striped")
            upc = "N/A"
            availability_num = "N/A"
            if product_table:
                rows = product_table.find_all("tr")
                for row in rows:
                    th = row.find("th")
                    td = row.find("td")
                    if th and td:
                        if "UPC" in th.text:
                            upc = td.text.strip()
                        elif "Availability" in th.text:
                            availability_num = td.text.strip()
            price_value = extract_price_value(price)
            stock_match = re.search(r'(\d+)', availability)
            stock_count = int(stock_match.group(1)) if stock_match else 0
            all_books.append({
                "Title": title,
                "Price": price,
                "Price_Value": price_value,
                "Availability": availability,
                "Stock_Count": stock_count,
                "Rating": rating,
                "Image": img_url,
                "Category": category,
                "UPC": upc
            })
    return pd.DataFrame(all_books)

if st.button("🚀 Scrape Books"):
    with st.spinner("Scraping book data..."):
        df = scrape_books(pages)
        st.success(f"✅ Scraped {len(df)} books from {pages} page(s).")
        st.session_state.df = df

if 'df' in st.session_state:
    df = st.session_state.df
    st.markdown("---")
    st.subheader("🎯 Advanced Filters")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**📂 Category Filter**")
        categories = sorted(df["Category"].unique())
        selected_categories = st.multiselect("Select Categories", categories, default=categories)
        st.markdown("**⭐ Rating Filter**")
        min_rating = st.slider("Minimum Rating", 1, 5, 1, key="rating_filter")

    with col2:
        st.markdown("**💰 Price Filter**")
        min_price = float(df["Price_Value"].min())
        max_price = float(df["Price_Value"].max())
        price_range = st.slider("Price Range (£)", min_value=min_price, max_value=max_price,
                                value=(min_price, max_price), step=0.1, key="price_filter")
        st.markdown("**📦 Availability Filter**")
        in_stock_only = st.checkbox("Show only in-stock books", value=False)

    with col3:
        st.markdown("**📊 Stock Count Filter**")
        min_stock = st.number_input("Minimum Stock Count", min_value=0, max_value=int(df["Stock_Count"].max()), value=0)
        st.markdown("**🔍 Title Search**")
        title_search = st.text_input("Search in title", "")

    filtered_df = df[
        (df["Category"].isin(selected_categories)) &
        (df["Rating"] >= min_rating) &
        (df["Price_Value"] >= price_range[0]) &
        (df["Price_Value"] <= price_range[1]) &
        (df["Stock_Count"] >= min_stock)
    ]

    if in_stock_only:
        filtered_df = filtered_df[filtered_df["Stock_Count"] > 0]

    if title_search:
        filtered_df = filtered_df[filtered_df["Title"].str.contains(title_search, case=False, na=False)]

    st.markdown("---")
    st.subheader("📊 Filter Results Summary")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Books", len(filtered_df))
    with col2:
        st.metric("Avg Rating", f"{filtered_df['Rating'].mean():.1f}" if len(filtered_df) > 0 else "N/A")
    with col3:
        st.metric("Avg Price", f"£{filtered_df['Price_Value'].mean():.2f}" if len(filtered_df) > 0 else "N/A")
    with col4:
        st.metric("Categories", len(filtered_df["Category"].unique()) if len(filtered_df) > 0 else 0)

    st.markdown("---")
    st.subheader("🔄 Sort Options")
    sort_col1, sort_col2 = st.columns(2)

    with sort_col1:
        sort_by = st.selectbox("Sort by", ["Title", "Price_Value", "Rating", "Category", "Stock_Count"], index=0)
    with sort_col2:
        sort_order = st.radio("Sort order", ["Ascending", "Descending"], horizontal=True)

    ascending = sort_order == "Ascending"
    filtered_df = filtered_df.sort_values(by=sort_by, ascending=ascending)

    st.markdown("---")
    st.markdown(f"### 📘 Filtered Results ({len(filtered_df)} books)")

    if len(filtered_df) > 0:
        for _, row in filtered_df.iterrows():
            stars = f"<span style='color:gold;font-size:18px;'>{'★' * int(row['Rating'])}{'☆' * (5 - int(row['Rating']))}</span>"
            stock_status = "✅ In Stock" if row['Stock_Count'] > 0 else "❌ Out of Stock"
            stock_color = "green" if row['Stock_Count'] > 0 else "red"
            st.markdown(f"""
            <div style="display: flex; align-items: center; margin-bottom: 15px; padding: 15px; border: 1px solid #ddd; border-radius: 10px; background-color: #808080;">
                <img src="{row['Image']}" width="80" style="margin-right: 15px; border-radius: 5px;" />
                <div style="flex-grow: 1;">
                    <h4 style="margin-bottom: 5px; color: #333;">{row['Title']}</h4>
                    <p style="margin: 2px 0;">💰 <b>{row['Price']}</b> | 📦 <span style="color: {stock_color};">{stock_status}</span> ({row['Stock_Count']} available)</p>
                    <p style="margin: 2px 0;">⭐ {stars} | 📂 {row['Category']}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("📥 Download Options")
        col1, col2 = st.columns(2)

        with col1:
            csv_filtered = filtered_df.drop(columns=["Image"]).to_csv(index=False).encode("utf-8")
            st.download_button("📥 Download Filtered Results (CSV)", data=csv_filtered,
                               file_name="books_filtered.csv", mime="text/csv")
        with col2:
            csv_all = df.drop(columns=["Image"]).to_csv(index=False).encode("utf-8")
            st.download_button("📥 Download All Results (CSV)", data=csv_all,
                               file_name="books_all.csv", mime="text/csv")

        st.markdown("---")
        st.subheader("📈 Quick Analytics")

        if len(filtered_df) > 0:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**📂 Books by Category**")
                category_counts = filtered_df["Category"].value_counts()
                st.bar_chart(category_counts)
            with col2:
                st.markdown("**⭐ Rating Distribution**")
                rating_counts = filtered_df["Rating"].value_counts().sort_index()
                st.bar_chart(rating_counts)
    else:
        st.warning("No books match your current filters. Try adjusting the filter criteria.")
else:
    st.info("👆 Click 'Scrape Books' to start scraping and filtering book data!")
