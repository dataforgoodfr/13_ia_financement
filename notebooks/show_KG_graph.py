# import networkx as nx
# from pyvis.network import Network

# # Load the GraphML file
# G = nx.read_graphml('./data/graph_chunk_entity_relation.graphml')

# # Create a Pyvis network
# net = Network(notebook=True)

# # Convert NetworkX graph to Pyvis network
# net.from_nx(G)

# # Save and display the network
# net.show('knowledge_graph.html')



#====v2
# import networkx as nx
# from pyvis.network import Network

# # Load the GraphML file
# G = nx.read_graphml('./data/lightrag_db/graph_chunk_entity_relation.graphml')

# # Create a Pyvis network with cdn_resources set to 'in_line'
# net = Network(notebook=True, height='1080px', width='100%', bgcolor='white', font_color='black', )#cdn_resources='in_line')

# # Convert NetworkX graph to Pyvis network
# net.from_nx(G)

# # Node customization
# for node in net.nodes:
#     # Check if 'title' exists and if 'type' is within it
#     if 'title' in node and isinstance(node['title'], dict) and 'type' in node['title']:
#         if node['title']['type'] == 'important':
#             node['color'] = '#FF5733'
#         else:
#             node['color'] = '#33FF57'
#     else:
#         # Default color if 'title' or 'type' is missing
#         node['color'] = '#808080'

#     # Example: Set node size based on degree
#     node['size'] = G.degree[node['id']] * 2

#     # Add hover information (safely accessing attributes)
#     node_info = f"Node: {node.get('label', 'Unknown')}"
#     if 'title' in node and isinstance(node['title'], dict):
#         node_info += f"<br>Type: {node['title'].get('type', 'N/A')}"
#     node['title'] = node_info

# # Edge customization
# for edge in net.edges:
#     # Example: Set edge width based on weight (if available)
#     if 'weight' in edge:
#         edge['width'] = min(edge['weight'], 10)  # Cap the width to avoid excessively thick edges
#     else:
#         edge['width'] = 2  # Default width

#     # Optionally, add hover information for edges
#     edge['title'] = f"Weight: {edge.get('weight', 'N/A')}"

# # Physics settings for better layout
# net.physics = True
# net.options = {
#     "physics": {
#         "enabled": True,
#         "stabilization": {"iterations": 1000},
#         "barnesHut": {"gravitationalConstant": -8000, "springLength": 200}
#     }
# }

# # Save and display the network
# net.show('knowledge_graph.html')


#=======v3
import networkx as nx
from pyvis.network import Network

# Load the GraphML file
G = nx.read_graphml('./data/lightrag_db/graph_chunk_entity_relation.graphml')

# Create a Pyvis network
net = Network(notebook=True, height='1080px', width='100%', bgcolor='white', font_color='black', cdn_resources='in_line')

# Convert NetworkX graph to Pyvis network
net.from_nx(G)


tableau_colors = [
    "#4E79A7",  # Blue
    "#F28E2B",  # Orange
    "#E15759",  # Red
    "#76B7B2",  # Teal
    "#59A14F",  # Green
    "#EDC949",  # Yellow
    "#AF7AA1",  # Purple
    "#FF9DA7",  # Pink
    "#9C755F",  # Brown
    #"#BAB0AC",  # Gray
    "#8CD17D",  # Light Green
    "#F1CE63",  # Light Yellow
    "#B0AFC3",  # Lavender
    "#FFBE7D",  # Peach
    "#D3D3D3"   # Light Gray
]

# Define color mapping for node groups
color_mapping = {}
entity_types_set=set(n["entity_type"] for n in net.nodes)
for entity in entity_types_set:
    if entity=="UNKNOWN":
        color_mapping[entity]= "#BAB0AC"#gray
    elif entity!="UNKNOWN" and len(tableau_colors)>0:
        color_mapping[entity]= tableau_colors.pop()


# Node customization with proper checks for attributes
for node in net.nodes:#[:50]:

    # Example: Set node size based on degree
    node['size'] = G.degree[node['id']] * 2

    # Set node color based on group (if available)
    node['color'] = color_mapping[node['entity_type']]
    
    # Add hover information (safely accessing attributes)
    descr=node["description"].split("<SEP>")[0]
    descr=descr+" ..." if len(descr)>100 else descr
    node_info = f"Node: {node.get('label')}\nNode type: {node['entity_type']} \nDescr: {descr}"
    if 'group' in node:
        node_info += f"<br>Group: {node['group']}"
    node['title'] = node_info

# Edge customization
for edge in net.edges:
    # Disable arrows
    edge['arrows'] = 'to' if False else None
    
    # Reduce edge width
    edge['width'] = 1

# Physics settings for better layout
net.physics = True
net.options = {
    "physics": {
        "enabled": True,
        "stabilization": {"iterations": 1000},
        "barnesHut": {"gravitationalConstant": -8000, "springLength": 200}
    }
}

# Save and display the network
net.show('knowledge_graph.html')