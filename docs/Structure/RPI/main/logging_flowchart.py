import graphviz

# Create a Graphviz flowchart for the logging.py script
dot = graphviz.Digraph(comment='Logging Flowchart', format='png')

# Define node styles
dot.attr('node', shape='box', style='filled', fillcolor='lightyellow', fontsize='12')
dot.attr('edge', fontsize='10')

# Nodes
dot.node('A', 'Setup Logging\n(Console, Files)')
dot.node('B', 'Create Logger\n(museum)')
dot.node('C', 'Add Console Handler\n(Color Support)')
dot.node('D', 'Create Log Directory\n(~/museum-system/logs)')
dot.node('E', 'Add File Handlers\n(museum.log, warnings,\nerrors, daily)')
dot.node('F', 'Set Level Filters\n(Warnings, Errors)')
dot.node('G', 'Log Startup Message')
dot.node('H', 'Handle Uncaught Exceptions')

# Edges
dot.edge('A', 'B', label='Start')
dot.edge('B', 'C', label='Create Logger')
dot.edge('C', 'D', label='Add Console')
dot.edge('D', 'E', label='Setup Directory')
dot.edge('E', 'F', label='Add File Handlers')
dot.edge('F', 'G', label='Set Filters')
dot.edge('G', 'H', label='Log Startup')
dot.edge('H', 'A', label='Handle Exceptions', style='dashed')

# Styling
dot.attr(dpi='300', fontsize='12', labelloc='t', label='Logging Flowchart\n(Museum System)', labeljust='c')
dot.attr(bgcolor='lightgrey', rankdir='TB', splines='polyline')

# Render
dot.render('/home/admin/Documents/GitHub/museum-system/docs/Structure/RPI/logging_flowchart.png', view=False)