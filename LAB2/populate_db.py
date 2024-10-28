from sqlalchemy import Column, Integer, String, Float, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import requests
from bs4 import BeautifulSoup

# Set up SQLAlchemy
DATABASE_URL = "sqlite:///products.db"
Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Define the Product table
class Product(Base):
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    link = Column(String, unique=True, nullable=False)
    sizes = Column(String, nullable=True)  # Sizes stored as comma-separated values

# Create the table in the SQLite database
Base.metadata.create_all(engine)

# Scraping function
def scrape_products():
    url = "https://prosport.md/ro/product-category/ghete/"  # Example URL; adjust as needed
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    products = []
    for product_item in soup.select('.product-grid-item'):
        name = product_item.select_one('.wd-entities-title a').text.strip()
        price_text = product_item.select_one('.woocommerce-Price-amount bdi').text.replace(',', '').replace('MDL', '').strip()
        price = float(price_text) if price_text.isdigit() else None
        link = product_item.select_one('.wd-entities-title a')['href']
        
        # Extract sizes (this assumes the sizes are on the product page)
        product_page = requests.get(link)
        product_soup = BeautifulSoup(product_page.text, 'html.parser')
        sizes = []
        size_elements = product_soup.select('select[name="attribute_pa_marime"] option')
        for size_element in size_elements:
            size = size_element.text.strip()
            if size:  # Ensure there's a valid size
                sizes.append(size)
        
        products.append({
            'name': name,
            'price': price,
            'link': link,
            'sizes': ', '.join(sizes) if sizes else 'Unknown'
        })
    return products

# Function to insert scraped data into the database
def save_to_database(products):
    db = SessionLocal()
    for product_data in products:
        # Check if the product already exists by its unique link
        existing_product = db.query(Product).filter(Product.link == product_data['link']).first()
        if not existing_product:
            # Insert new product
            new_product = Product(
                name=product_data['name'],
                price=product_data['price'],
                link=product_data['link'],
                sizes=product_data['sizes']
            )
            db.add(new_product)
    db.commit()
    db.close()
    print("Data has been successfully saved to the database.")

# Run scraping and save to database
products = scrape_products()
save_to_database(products)
