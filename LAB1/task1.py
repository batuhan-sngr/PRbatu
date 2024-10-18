import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import socket
import json

# Convert MDL to EUR
MDL_TO_EUR = 0.052

# Convert EUR to MDL
EUR_TO_MDL = 1 / MDL_TO_EUR

# Step 2: Function to make an HTTP GET request
def get_html(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        raise Exception(f"Failed to fetch data, status code: {response.status_code}")

# Step 3: Extract name, price, and link of products
def extract_products(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find all product grid items
    products = []
    for product in soup.select('.product-grid-item'):
        # Extract the name of the product
        name_tag = product.select_one('.wd-entities-title a')
        name = name_tag.text.strip() if name_tag else None
        
        # Extract the product link
        link = name_tag['href'] if name_tag else None
        
        # Extract the price (discounted price if available, otherwise regular price)
        price_tag = product.select_one('.wrap-price ins .woocommerce-Price-amount bdi') or \
                    product.select_one('.wrap-price del .woocommerce-Price-amount bdi')
        if price_tag:
            price = int(price_tag.text.replace(',', '').replace('MDL', '').strip())
        else:
            price = None

        # Append the product data if valid
        if name and price and link:
            products.append({'name': name, 'price': price, 'link': link})
    
    return products

# Step 4: Scrape additional product details (sizes)
def scrape_additional_details(product):
    html_content = get_html(product['link'])
    soup = BeautifulSoup(html_content, 'html.parser')

    # Find the specific product's size container
    sizes = []
    size_container = soup.select_one('.variations')  # This targets the table with sizes

    if size_container:
        # Extract size options from the dropdown or swatches
        size_options = size_container.select('select[name="attribute_pa_marime"] option')
        
        for option in size_options:
            if option['value']:  # Ensure the option has a value
                sizes.append(option.text.strip())  # Get the text for each size

    # Join the sizes into a string separated by commas or store as a list
    product['sizes'] = ', '.join(sizes) if sizes else 'Unknown'


# Step 5: Validate product data
def validate_product(product):
    product['name'] = product['name'].strip()
    assert isinstance(product['price'], int), "Price should be an integer"

# Step 6: Process products using Map/Filter/Reduce
def process_products(products, price_range=(100, 10000)):
    # Convert MDL to EUR or EUR to MDL based on product price
    for product in products:
        if 'EUR' in product.get('currency', 'MDL'):
            product['price'] = int(product['price'] * EUR_TO_MDL)
        else:
            product['price'] = int(product['price'] * MDL_TO_EUR)
    
    # Filter products by price range
    filtered_products = list(filter(lambda p: price_range[0] <= p['price'] <= price_range[1], products))
    
    # Calculate the total price of filtered products
    total_price = sum(product['price'] for product in filtered_products)
    
    # Attach UTC timestamp (timezone-aware)
    utc_timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    
    return {
        'products': filtered_products,
        'total_price': total_price,
        'timestamp': utc_timestamp
    }

# Step 7: Use TCP sockets to make an HTTP request
def fetch_using_socket(url):
    host = url.split("//")[-1].split("/")[0]
    port = 80
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    
    request = f"GET {url} HTTP/1.1\r\nHost: {host}\r\n\r\n"
    sock.send(request.encode())
    
    response = sock.recv(4096).decode()
    sock.close()
    
    return response.split("\r\n\r\n")[1]  # Return the body of the response

# Step 8: Manual serialization to JSON and XML
def serialize_to_json(data):
    return json.dumps(data, indent=4)

def serialize_to_xml(data):
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<products>\n'
    for product in data['products']:
        xml += '  <product>\n'
        for key, value in product.items():
            xml += f'    <{key}>{value}</{key}>\n'
        xml += '  </product>\n'
    xml += f'  <total_price>{data["total_price"]}</total_price>\n'
    xml += f'  <timestamp>{data["timestamp"]}</timestamp>\n'
    xml += '</products>'
    return xml


# Step 10: Main function
def main():
    url = "https://prosport.md/ro/product-category/ghete/"  # Example URL, adjust based on actual site structure
    html_content = get_html(url)
    
    # Extract products
    products = extract_products(html_content)
    
    # Scrape additional details for each product
    for product in products:
        scrape_additional_details(product)
        validate_product(product)
    
    # Process products (e.g., filtering, conversion)
    processed_data = process_products(products)
    
    # Serialize to JSON and XML
    json_data = serialize_to_json(processed_data)
    xml_data = serialize_to_xml(processed_data)
    
    # Custom serialization using the scraped and processed data
    custom_data = custom_serialize(processed_data)
    
    # Output results
    print("JSON Data:")
    print(json_data)
    print("\nXML Data:")
    print(xml_data)
    print("\nCustom Serialized Data:")
    print(custom_data)
    
    # Test custom deserialization with the scraped data
    deserialized_data = custom_deserialize(custom_data)
    print("\nCustom Deserialized Data:")
    print(deserialized_data)
    
    # Step 11: Send data to localhost:8000/upload
    send_data_to_server(json_data, xml_data)

def custom_serialize(data):
    if isinstance(data, dict):
        items = []
        for key, value in data.items():
            serialized_key = f"k:str({key})"
            serialized_value = f"v:{custom_serialize(value)}"
            items.append(f"{serialized_key}:{serialized_value}")
        return f"D:{{{'; '.join(items)}}}"
    elif isinstance(data, list):
        items = [custom_serialize(item) for item in data]
        return f"L:[{';'.join(items)};]"
    elif isinstance(data, int):
        return f"int({data})"
    elif isinstance(data, str):
        return f"str({data})"
    else:
        raise TypeError(f"Unsupported data type: {type(data)}")

def custom_deserialize(serialized_data):
    if serialized_data.startswith("D:{") and serialized_data.endswith("}"):
        # Deserialize dictionary
        items = serialized_data[3:-1].split("; ")
        result_dict = {}
        for item in items:
            if item:
                # Only split at the first occurrence of ":v:"
                if ":v:" in item:
                    key_part, value_part = item.split(":v:", 1)
                    key = custom_deserialize(key_part[6:-1]) if key_part.startswith("k:str(") else key_part
                    value = custom_deserialize(value_part)
                    result_dict[key] = value
        return result_dict
    elif serialized_data.startswith("L:[") and serialized_data.endswith("];"):
        # Deserialize list
        items = serialized_data[3:-2].split(";")
        return [custom_deserialize(item) for item in items if item]
    elif serialized_data.startswith("int(") and serialized_data.endswith(")"):
        return int(serialized_data[4:-1])
    elif serialized_data.startswith("str(") and serialized_data.endswith(")"):
        return serialized_data[4:-1]
    else:
        # Return the plain string if it does not match any serialization format
        return serialized_data


# Step 11: Sending serialized data to server
def send_data_to_server(json_data, xml_data):
    url = "http://localhost:8000/upload"
    
    # Send the JSON data
    headers_json = {
    'Content-Type': 'application/json',
    "Authorization": "Basic NTAwOjIwNA=="
    }

    response_json = requests.post(url, data=json_data, headers=headers_json)
    
    if response_json.status_code == 200:
        print("JSON data successfully sent!")
    else:
        print(f"Failed to send JSON data, status code: {response_json.status_code}")
    
    # Send the XML data
    headers_xml = {'Content-Type': 'application/xml',
    "Authorization": "Basic NTAwOjIwNA==",
    "Content-Length": str(len(xml_data.encode('utf-8')))
    }
    
    response_xml = requests.post(url, data=xml_data.encode('utf-8'), headers=headers_xml)
    
    if response_xml.status_code == 200:
        print("XML data successfully sent!")
    else:
        print(f"Failed to send XML data, status code: {response_xml.status_code}")

if __name__ == "__main__":
    main()
