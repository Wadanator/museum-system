import graphviz

# Create a Graphviz flowchart for the web.py script
dot = graphviz.Digraph(comment='Web Dashboard Flowchart', format='png')

# Define node styles
dot.attr('node', shape='box', style='filled', fillcolor='lightgreen', fontsize='12')
dot.attr('edge', fontsize='10')

# Nodes
dot.node('A', 'Start Web Dashboard')
dot.node('B', 'Setup Flask App\n(Configure SocketIO)')
dot.node('C', 'Setup Log Handler\n(WebLogHandler)')
dot.node('D', 'Load Existing Logs\n(from museum.log)')
dot.node('E', 'Setup Routes\n(/status, /logs, /scenes,\n/run_scene, /stop_scene, /restart)')
dot.node('F', 'Client Connected?', shape='diamond', fillcolor='yellow')
dot.node('G', 'Emit Log History\nand Status')
dot.node('H', 'Handle Web Request', shape='diamond', fillcolor='yellow')
dot.node('I', 'Run Scene Request?', shape='diamond', fillcolor='yellow')
dot.node('J', 'Trigger Scene\n(Load and Run, Log Info)')
dot.node('K', 'Other Request\n(Stop Scene, Restart, Logs, Status)')
dot.node('L', 'Process Request\n(Update Log Buffer)')
dot.node('M', 'Broadcast Log\n(via SocketIO)')
dot.node('N', 'Continue Running', shape='diamond', fillcolor='yellow')

# Edges
dot.edge('A', 'B', label='Start')
dot.edge('B', 'C', label='Initialize')
dot.edge('C', 'D', label='Setup Logging')
dot.edge('D', 'E', label='Load Logs')
dot.edge('E', 'F', label='Setup Routes')
dot.edge('F', 'G', label='Yes')
dot.edge('F', 'H', label='No')
dot.edge('G', 'H', label='Emit Data')
dot.edge('H', 'I', label='Receive Request')
dot.edge('I', 'J', label='Yes')
dot.edge('I', 'K', label='No')
dot.edge('J', 'L', label='Trigger Scene')
dot.edge('K', 'L', label='Process')
dot.edge('L', 'M', label='Update')
dot.edge('M', 'N', label='Broadcast Log')
dot.edge('N', 'F', label='Continue', style='dashed')

# Styling
dot.attr(dpi='300', fontsize='12', labelloc='t', label='Web Dashboard Flowchart\n(Flask and SocketIO)', labeljust='c')
dot.attr(bgcolor='lightgrey', rankdir='TB', splines='polyline')

# Render
dot.render('/home/admin/Documents/GitHub/museum-system/docs/Structure/RPI/web_flowchart.png', view=False)