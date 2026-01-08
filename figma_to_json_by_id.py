import requests
import json
import os
import sys

# Constants provided by the user
FIGMA_TOKEN = "figma_token"
FILE_KEY = "file_key"
# This acts as the Node ID
NODE_ID = "node_id"

def main():
    # Define the output directory
    output_dir = "json"
    
    # Create the directory if it doesn't exist
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
            print(f"Created directory: {output_dir}")
        except OSError as e:
            print(f"Error creating directory {output_dir}: {e}")
            sys.exit(1)

    # Figma API endpoint to get a specific node
    # The 'ids' parameter takes comma-separated node IDs
    url = f"https://api.figma.com/v1/files/{FILE_KEY}/nodes?ids={NODE_ID}"

    headers = {
        "X-Figma-Token": FIGMA_TOKEN
    }

    print(f"Fetching data for Node ID: {NODE_ID} from File Key: {FILE_KEY}...")

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status() # Raise error for bad status codes (4xx, 5xx)

        data = response.json()

        # Check if the node actually exists in the response
        nodes = data.get("nodes", {})
        # Note: Figma API might return keys with ':' replaced by '-' or implementation details.
        # But usually it keys by the ID requested.
        # Node IDs in response keys might be like "188:210" even if requested as "188-210" or vice-versa depending on the input format flexibility.
        # Let's inspect what we got if we want to be robust, but here we dump the whole response as per "give the json for this id only".
        # If the user wants JUST the node object, we might need to drill down. 
        # "give the json for this id only" -> usually implies the response for that ID.
        # The Figma API response structure for 'nodes' is: { "name": ..., "lastModified": ..., "nodes": { "id": { ... } } }
        # I will save the entire response to preserve context, or just the node. 
        # "give the json for this id only" -> likely means the JSON representation of that node.
        
        # Let's try to extract the specific node if possible to be more helpful, 
        # but saving the full response is safer to ensure no data loss. 
        # However, the user said "json for this id ONLY", so maybe they want just the node content?
        # I will stick to saving the API response which contains the node. 
        
        # Proper filename handling (replace invalid chars for filenames)
        safe_node_id = NODE_ID.replace(':', '_').replace('-', '_')
        filename = f"{safe_node_id}.json"
        file_path = os.path.join(output_dir, filename)

        with open(file_path, "w") as f:
            json.dump(data, f, indent=4)

        print(f"Successfully saved JSON to {file_path}")

    except requests.exceptions.HTTPError as err:
        print(f"HTTP Error: {err}")
        print(f"Response Body: {response.text}")
    except Exception as err:
        print(f"An error occurred: {err}")

if __name__ == "__main__":
    main()
