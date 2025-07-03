import graphviz

# Create a Graphviz flowchart for MQTTClient class focusing on connection and disconnection
dot = graphviz.Digraph(comment='MQTT Client Flowchart', format='png')

# Define node styles
dot.attr('node', shape='box', style='filled', fillcolor='lightblue', fontsize='12')
dot.attr('edge', fontsize='10')

# MQTT Client Nodes
dot.node('A', 'Initialize MQTTClient\n(Set Broker, Port, Client ID, Callbacks)\n[External]', fillcolor='lightcyan')
dot.node('B', 'Connect to Broker\n(client.connect)\n[External]', shape='diamond', fillcolor='yellow')
dot.node('C', 'Connection Successful?\n(Return Code == 0)\n[Internal]', shape='diamond', fillcolor='yellow')
dot.node('D', 'Set connected=True\n(Log Info: Connected)\n[Internal]')
dot.node('E', 'Set connected=False\n(Log Error: Failed to Connect)\n[Internal]')
dot.node('F', 'Wait for Connection\n(Check Timeout)\n[External]', shape='diamond', fillcolor='yellow')
dot.node('G', 'Log Error\n(Connection Timeout)\n[External]')
dot.node('H', 'Return connected=False\n[External]')
dot.node('I', 'Check Connection\n(is_connected())\n[External]', shape='diamond', fillcolor='yellow')
dot.node('J', 'On Disconnect Callback\n(Set connected=False, Log Warning)\n[Internal]')
dot.node('K', 'Disconnect\n(Stop Loop, Disconnect, Log)\n[External]')
dot.node('L', 'Return to Main Loop\n[External]')
dot.node('M', 'Publish Message\n(Check Connected, Publish)\n[External]', fillcolor='lightgreen')
dot.node('N', 'Subscribe to Topic\n(Check Connected, Subscribe)\n[External]', fillcolor='lightgreen')

# Add edges with labels to show flow and decisions
dot.edge('A', 'B', label='Start Connection')
dot.edge('B', 'C', label='Attempt Connect')
dot.edge('C', 'D', label='Yes (rc=0)')
dot.edge('C', 'E', label='No (rc!=0)')
dot.edge('D', 'F', label='Log Success')
dot.edge('E', 'F', label='Log Failure')
dot.edge('F', 'D', label='Connected')
dot.edge('F', 'G', label='Timeout')
dot.edge('G', 'H', label='Log Timeout')
dot.edge('H', 'L', label='Return False')
dot.edge('I', 'L', label='Yes (Connected)')
dot.edge('I', 'J', label='No (Disconnected)')
dot.edge('J', 'L', label='Log Warning')
dot.edge('D', 'M', label='Optional: Publish')
dot.edge('D', 'N', label='Optional: Subscribe')
dot.edge('M', 'L', label='After Publish')
dot.edge('N', 'L', label='After Subscribe')
dot.edge('L', 'K', label='Optional: Disconnect')
dot.edge('K', 'L', label='Log Disconnect')

# Add a legend to clarify external vs. internal methods
with dot.subgraph(name='cluster_legend') as legend:
    legend.attr(label='Legend', fontsize='10', style='filled', fillcolor='white')
    legend.node('L1', 'External Method\n(Called by User)', shape='box', fillcolor='lightblue')
    legend.node('L2', 'Internal Callback\n(MQTT Library)', shape='box', fillcolor='yellow')
    legend.node('L3', 'Optional Action\n(Example Usage)', shape='box', fillcolor='lightgreen')

# Add styling for clarity and presentation
dot.attr(dpi='300', fontsize='12', labelloc='t', label='MQTT Client Flowchart\n(Connection, Disconnection, and Example Usage)', labeljust='c')
dot.attr(bgcolor='lightgrey', rankdir='TB', splines='polyline')

# Render the flowchart
dot.render('/home/admin/Documents/GitHub/museum-system/docs/Structure/RPI/mqtt_client_flowchart.png', view=False)