import graphviz

# Create a Graphviz flowchart for the watchdog.py script
dot = graphviz.Digraph(comment='Watchdog Flowchart', format='png')

# Define node styles
dot.attr('node', shape='box', style='filled', fillcolor='lightcoral', fontsize='12')
dot.attr('edge', fontsize='10')

# Nodes
dot.node('A', 'Start Watchdog')
dot.node('B', 'Setup Logging\n(museum.log, warnings, errors)', fillcolor='lightyellow')
dot.node('C', 'Initialize Watchdog\n(Set CPU/Mem Thresholds)')
dot.node('D', 'Watchdog Loop')
dot.node('E', 'Service Running?', shape='diamond', fillcolor='yellow')
dot.node('F', 'Start/Restart Service\n(Log Warning)')
dot.node('G', 'Check Process Health\n(CPU > 45%, Mem > 512MB)', shape='diamond', fillcolor='yellow')
dot.node('H', 'Process Healthy?', shape='diamond', fillcolor='yellow')
dot.node('I', 'Check Network\n(Log Warning if Lost)')
dot.node('J', 'Log Health Status\n(CPU, Mem, if Needed)')
dot.node('K', 'Exit (User Interrupt)', shape='ellipse', fillcolor='red')

# Edges
dot.edge('A', 'B', label='Start')
dot.edge('B', 'C', label='Setup Logging')
dot.edge('C', 'D', label='Initialize')
dot.edge('D', 'E', label='Periodic Check')
dot.edge('E', 'F', label='No')
dot.edge('E', 'G', label='Yes')
dot.edge('G', 'H', label='Check Health')
dot.edge('H', 'F', label='No (High CPU/Mem)')
dot.edge('H', 'I', label='Yes')
dot.edge('I', 'J', label='Check Network')
dot.edge('J', 'D', label='Log (if needed)', style='dashed')
dot.edge('F', 'D', label='After Restart', style='dashed')
dot.edge('D', 'K', label='User Interrupt', style='dashed')

# Styling
dot.attr(dpi='300', fontsize='12', labelloc='t', label='Watchdog Flowchart\n(Museum System Monitoring)', labeljust='c')
dot.attr(bgcolor='lightgrey', rankdir='TB', splines='polyline')

# Render
dot.render('/home/admin/Documents/GitHub/museum-system/docs/Structure/RPI/watchdog_flowchart.png', view=False)