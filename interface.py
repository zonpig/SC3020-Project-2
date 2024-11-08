# GUI Imports
import customtkinter
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image

# Backend Imports
import matplotlib

matplotlib.use("Agg")  # Use a non-GUI backend suitable for multi-threaded environments
import matplotlib.pyplot as plt
import networkx as nx
import os
from networkx.drawing.nx_agraph import graphviz_layout
from flask import Flask
import time

# Code for backend
app = Flask(__name__)

def build_graph(G, node, parent=None, edge_label=""):
    node_id = f"{node['Node Type']}_{G.number_of_nodes()}"
    buffer = sum(
        node.get(key, 0)
        for key in [
            "Shared Hit Blocks",
            "Shared Read Blocks",
            "Shared Dirtied Blocks",
            "Shared Written Blocks",
        ]
    )
    total_cost = node.get("Total Cost", "N/A")
    row_size = node.get("Actual Rows", "N/A")

    # Determine if the current node is a leaf node
    is_leaf = "Plans" not in node or len(node["Plans"]) == 0

    # Append the Relation Name for leaf nodes
    relation_name = node.get("Relation Name", "")
    if is_leaf and relation_name:
        label = (
            f"<{relation_name}>\nCost: {total_cost}\nBuffer: {buffer}\nRows: {row_size}"
        )
    else:
        label = f"Cost: {total_cost}\nBuffer: {buffer}\nRows: {row_size}"

    G.add_node(node_id, label=label, type=node["Node Type"])
    if parent:
        G.add_edge(parent, node_id)

    if not is_leaf:
        for child in node["Plans"]:
            build_graph(G, child, node_id)


def visualize_query_plan(plan):
    G = nx.DiGraph()
    build_graph(G, plan)
    pos = graphviz_layout(G, prog="dot")

    plt.figure(figsize=(15, 10))  # Adjust the figure size

    # Draw nodes with custom shape and style
    nx.draw_networkx_nodes(
        G, pos, node_shape="o", node_size=500, node_color="lightblue", alpha=0.7
    )

    # Draw edges
    nx.draw_networkx_edges(G, pos, arrows=True)

    # Draw labels for details
    details_labels = {node: G.nodes[node]["label"] for node in G.nodes}
    type_labels = {node: G.nodes[node]["type"] for node in G.nodes}

    # Adjust label positions if necessary
    label_pos = {node: (pos[node][0], pos[node][1] - 13) for node in G.nodes}
    type_label_pos = {node: (pos[node][0], pos[node][1] + 10) for node in G.nodes}

    nx.draw_networkx_labels(
        G, label_pos, details_labels, font_size=9, font_weight="bold"
    )
    nx.draw_networkx_labels(G, type_label_pos, type_labels, font_size=9)

    plt.axis("off")  # Turn off the axis
    plt.tight_layout()  # Adjust the layout
    fn = "query_plan_tree" + str(int(time.time())) + ".png"
    image_path = os.path.join(app.root_path, "static", fn)

    plt.savefig(image_path, format="png", bbox_inches="tight")
    plt.close()  # Ensure the plot is closed and memory is freed

    return fn

# Code for the GUI (you may use any other GUI development toolkit as long as it is compatible with Python)
customtkinter.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
customtkinter.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

class ToplevelWindow(customtkinter.CTkToplevel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # configure window
        self.title("SC3020 Project 2 View")
        self.geometry(f"{1280}x{720}")

        # configure grid layout (4x4)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure((2, 3), weight=0)
        self.grid_rowconfigure((0, 1, 2), weight=1)

        self.logo_label = customtkinter.CTkLabel(self, text="QEP is HERE", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=1, padx=20, pady=(20, 10))
        self.plot_frame = customtkinter.CTkFrame(self, width=640, height=480, corner_radius=0)
        self.plot_frame.grid(row=1, column=1, padx=20, pady=20)

        # create sidebar frame with widgets
        self.sidebar_frame = customtkinter.CTkFrame(self, width=280, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=2, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)
        
        self.sidebar_button_1 = customtkinter.CTkButton(self.sidebar_frame, command=self.display_plot, text='Display QEP')
        self.sidebar_button_1.grid(row=1, column=0, padx=20, pady=10)

        self.sidebar_button_2 = customtkinter.CTkButton(self.sidebar_frame, command=self.display_plot, text='Display AQP')
        self.sidebar_button_2.grid(row=2, column=0, padx=20, pady=10)

        self.sidebar_button_3 = customtkinter.CTkButton(self.sidebar_frame, command=self.compare_costs, text='Compare Costs')
        self.sidebar_button_3.grid(row=3, column=0, padx=20, pady=10)

    def display_plot(self):
        # Example query plan
        example_plan = {
            "Node Type": "Aggregate",
            "Total Cost": 100.0,
            "Actual Rows": 10,
            "Shared Hit Blocks": 5,
            "Shared Read Blocks": 10,
            "Shared Dirtied Blocks": 2,
            "Shared Written Blocks": 1,
            "Plans": [
                {
                    "Node Type": "Seq Scan",
                    "Relation Name": "employees",
                    "Total Cost": 50.0,
                    "Actual Rows": 1000,
                    "Shared Hit Blocks": 3,
                    "Shared Read Blocks": 5,
                    "Shared Dirtied Blocks": 1,
                    "Shared Written Blocks": 0,
                }
            ]
        }
        img = visualize_query_plan(example_plan)
        my_image = customtkinter.CTkImage(light_image=Image.open(f'static/{img}'), size=(960, 600))
        self.image_label = customtkinter.CTkLabel(self.plot_frame, image=my_image, text="")  # display image with a CTkLabel
        self.image_label.grid(row=0, column=0)
        print('end')

    def compare_costs(self):
        print("TO BE DONE")

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        # configure window
        self.title("SC3020 Project 2")
        self.geometry(f"{1100}x{580}")
        self.toplevel_window = None

        # configure grid layout (4x4)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure((2, 3), weight=0)
        self.grid_rowconfigure((0, 1, 2), weight=1)

        # create sidebar frame with widgets
        self.sidebar_frame = customtkinter.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)
        self.logo_label = customtkinter.CTkLabel(self.sidebar_frame, text="QEP Visualiser", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        self.appearance_mode_label = customtkinter.CTkLabel(self.sidebar_frame, text="Appearance Mode:", anchor="w")
        self.appearance_mode_label.grid(row=5, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = customtkinter.CTkOptionMenu(self.sidebar_frame, values=["Light", "Dark", "System"],
                                                                       command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=6, column=0, padx=20, pady=(10, 10))
        self.scaling_label = customtkinter.CTkLabel(self.sidebar_frame, text="UI Scaling:", anchor="w")
        self.scaling_label.grid(row=7, column=0, padx=20, pady=(10, 0))
        self.scaling_optionemenu = customtkinter.CTkOptionMenu(self.sidebar_frame, values=["80%", "90%", "100%", "110%", "120%"],
                                                               command=self.change_scaling_event)
        self.scaling_optionemenu.grid(row=8, column=0, padx=20, pady=(10, 20))

        # create main entry and button
        self.entry = customtkinter.CTkEntry(self, placeholder_text="What if ... ?")
        self.entry.grid(row=3, column=1, columnspan=2, padx=(20, 0), pady=(20, 20), sticky="nsew")

        self.main_button_1 = customtkinter.CTkButton(master=self, fg_color="transparent", border_width=2, text_color=("gray10", "#DCE4EE"), text='Generate SQL', command=self.generate_sql)
        self.main_button_1.grid(row=3, column=3, padx=(20, 20), pady=(20, 20), sticky="nsew")

        # create textbox
        self.textbox = customtkinter.CTkTextbox(self, width=500, height=720)
        self.textbox.grid(row=0, column=1, padx=(20, 0), pady=(20, 0), sticky="nsew")

        # create tabview
        self.tabview = customtkinter.CTkTabview(self, width=250)
        self.tabview.grid(row=0, column=3, padx=(20, 0), pady=(20, 0), sticky="nsew")
        self.tabview.add("Choose Schema")
        self.tabview.add("Query History")
        self.tabview.tab("Choose Schema").grid_columnconfigure(0, weight=1)  # configure grid of individual tabs
        self.tabview.tab("Query History").grid_columnconfigure(0, weight=1)

        self.optionmenu_1 = customtkinter.CTkOptionMenu(self.tabview.tab("Choose Schema"), dynamic_resizing=False,
                                                        values=["TPC-H", "Master", "SC3020"])
        self.optionmenu_1.grid(row=0, column=0, padx=20, pady=(20, 10))
        self.qep_button = customtkinter.CTkButton(self.tabview.tab("Choose Schema"), text="Visualise QEP",
                                                           command=self.visualise_qep)
        self.qep_button.grid(row=1, column=0, padx=20, pady=(10, 10))

        # set default values
        self.appearance_mode_optionemenu.set("Dark")
        self.scaling_optionemenu.set("100%")
        self.optionmenu_1.set("Schema")
        self.textbox.insert(index=0.0, text='Replace this for your Query !!')

    def visualise_qep(self):
        if self.toplevel_window is None or not self.toplevel_window.winfo_exists():
            self.toplevel_window = ToplevelWindow(self)  # create window if its None or destroyed
        self.toplevel_window.focus()  # if window exists focus it

    def change_appearance_mode_event(self, new_appearance_mode: str):
        customtkinter.set_appearance_mode(new_appearance_mode)

    def change_scaling_event(self, new_scaling: str):
        new_scaling_float = int(new_scaling.replace("%", "")) / 100
        customtkinter.set_widget_scaling(new_scaling_float)

    def generate_sql(self):
        self.textbox.delete(index1=0.0, index2='end')
        self.textbox.insert(index=0.0, text=f'{self.entry.get()}')

if __name__ == "__main__":
    gui = App()
    gui.mainloop()
