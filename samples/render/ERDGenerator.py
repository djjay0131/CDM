import json
import os
import random
from graphviz import Digraph

# Add Graphviz bin directory to PATH
graphviz_bin_path = r'C:\Program Files\Graphviz\bin'
if (graphviz_bin_path not in os.environ['PATH']):
    os.environ['PATH'] += os.pathsep + graphviz_bin_path

def load_json(filepath):
    with open(filepath, 'r') as file:
        return json.load(file)

def get_random_color():
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))

def get_contrasting_text_color(bgcolor):
    # Convert hex color to RGB
    r = int(bgcolor[1:3], 16)
    g = int(bgcolor[3:5], 16)
    b = int(bgcolor[5:7], 16)
    # Calculate luminance
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    # Return black for light colors and white for dark colors
    return "black" if luminance > 0.5 else "white"

def parse_entity(entity, graph, entity_colors):
    entity_name = entity['entityName']
    entity_description = entity.get('description', '')
    display_name = entity['displayName']
    attributes = entity['hasAttributes'][0]['attributeGroupReference']['members']
    bgcolor = entity_colors.get(entity_name, get_random_color())
    entity_colors[entity_name] = bgcolor
    text_color = get_contrasting_text_color(bgcolor)
    label = f"""< 
    <table border="0" cellborder="1" cellspacing="0" bgcolor="{bgcolor}">
        <tr><td><b><font color="{text_color}">{display_name}</font></b></td></tr>
        <tr><td><table border="0" cellborder="0" cellspacing="0"><tr><td width="100%" height="1" bgcolor="black"></td></tr></table></td></tr>
        {"".join([f"<tr><td bgcolor='{entity_colors.get(attr['entity']['source'].get('entityName') if isinstance(attr['entity']['source'], dict) else attr['entity']['source'], bgcolor)}'><font color='{get_contrasting_text_color(entity_colors.get(attr['entity']['source'].get('entityName') if isinstance(attr['entity']['source'], dict) else attr['entity']['source'], bgcolor))}'>{attr['name']}</font></td></tr>" if 'entity' in attr else f"<tr><td><font color='{text_color}'>{attr['name']}</font></td></tr>" for attr in attributes])}
    </table>
    >"""
    graph.node(entity_name, label=label, shape='box', tooltip=entity_description)

def add_relationships(entity, graph, entity_colors):
    entity_name = entity['entityName']
    for attribute in entity['hasAttributes'][0]['attributeGroupReference']['members']:
        if 'entity' in attribute:
            related_entity = attribute['entity']['source']
            if isinstance(related_entity, dict):
                related_entity = related_entity.get('entityName', related_entity.get('source'))
            if related_entity:
                graph.edge(entity_name, related_entity)
                if related_entity in entity_colors:
                    attribute['bgcolor'] = entity_colors[related_entity]

def parse_manifest(manifest_path, graph, entity_colors):
    manifest = load_json(manifest_path)
    for entity in manifest['entities']:
        entity_file, entity_name = entity['entityPath'].rsplit('/', 1)
        entity_path = os.path.join(os.path.dirname(manifest_path), entity_file)
        entity_definition = load_json(entity_path)
        parse_entity(entity_definition['definitions'][0], graph, entity_colors)
        add_relationships(entity_definition['definitions'][0], graph, entity_colors)

def generate_dependency_matrix(manifest_path, entity_colors, output_file="dependency_matrix.txt", graph_output="dependency_graph"):
    """
    Generate a dependency matrix for entities in the manifest.
    Determines the load order and identifies entities that can be loaded concurrently.
    Writes the output to a file and renders the dependency matrix as a graph.
    """
    with open(manifest_path, 'r') as file:
        manifest = json.load(file)

    # Extract entities and their dependencies
    entities = {}
    for definition in manifest.get('definitions', []):
        entity_name = definition['entityName'].lower()
        dependencies = set()
        for attribute in definition.get('hasAttributes', []):
            for member in attribute.get('attributeGroupReference', {}).get('members', []):
                if 'entity' in member and member['entity'].get('source'):
                    related_entity = member['entity']['source']
                    if isinstance(related_entity, dict):
                        related_entity = related_entity.get('entityName', related_entity.get('source')).lower()
                    else:
                        related_entity = related_entity.lower()
                    dependencies.add(related_entity)
        entities[entity_name] = dependencies

    # Topological sort to determine load order
    load_order = []
    while entities:
        independent_entities = [e for e, deps in entities.items() if not deps]
        if not independent_entities:
            raise ValueError("Circular dependency detected among entities.")
        load_order.append(independent_entities)
        for e in independent_entities:
            del entities[e]
        for deps in entities.values():
            deps.difference_update(independent_entities)

    # Write the matrix to a file
    with open(output_file, 'w') as f:
        f.write("Dependency Matrix:\n")
        for i, group in enumerate(load_order):
            f.write(f"Step {i + 1}: {', '.join(group)}\n")
            for entity in group:
                color = entity_colors.get(entity, "#FFFFFF")
                f.write(f"  - {entity} (color: {color})\n")

    # Render the dependency graph
    graph = Digraph("DependencyGraph", format="png")
    graph.attr(rankdir="TB")
    for i, group in enumerate(load_order):
        for entity in group:
            color = entity_colors.get(entity, "#FFFFFF")
            text_color = get_contrasting_text_color(color)
            graph.node(entity, label=entity, style="filled", fillcolor=color, fontcolor=text_color)
        if i > 0:
            for parent in load_order[i - 1]:
                for child in group:
                    graph.edge(parent, child)
    graph.render(graph_output, cleanup=True)

def main():
    base_path = r'C:\Code\CIDM\schemaDocuments\FinancialServices\PropertyandCasualtyDataModel'
    manifest_file = os.path.join(base_path, 'PropertyandCasualtyDataModel.1.0.1.manifest.cdm.json')

    # base_path = r'C:\Code\CIDM\schemaDocuments\core\applicationCommon'
    # manifest_file = os.path.join(base_path, 'applicationCommon.1.5.manifest.cdm.json')

    graph = Digraph(comment='Entity Relationship Diagram', graph_attr={'rankdir': 'LR', 'nodesep': '1', 'ranksep': '2'})
    entity_colors = {}
    parse_manifest(manifest_file, graph, entity_colors)
    
    erd_name = 'ERD2'
    graph.render(os.path.join(base_path, erd_name), format='svg', cleanup=True)

    # Generate HTML file with embedded SVG
    with open(os.path.join(base_path, f'{erd_name}.svg'), 'r') as svg_file:
        svg_content = svg_file.read()
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Entity Relationship Diagram</title>
    </head>
    <body>
        {svg_content}
    </body>
    </html>
    """
    
    with open(os.path.join(base_path, f'{erd_name}.html'), 'w') as html_file:
        html_file.write(html_content)

    generate_dependency_matrix(manifest_file, entity_colors)

if __name__ == "__main__":
    main()
