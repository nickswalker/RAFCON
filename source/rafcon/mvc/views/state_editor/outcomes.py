import gtk
from gtkmvc import View

from rafcon.mvc import gui_helper
from rafcon.mvc.utils import constants


class StateOutcomesTreeView(View):
    builder = constants.get_glade_path("outcome_list_widget.glade")
    top = 'tree_view'

    def __init__(self):
        View.__init__(self)
        self.tree_view = self['tree_view']


class StateOutcomesEditorView(View):
    top = 'main_frame'

    def __init__(self):
        View.__init__(self)

        self.vbox = gtk.VBox()
        self.treeView = StateOutcomesTreeView()
        self.tree = self.treeView['tree_view']

        add_button = gtk.Button('Add')
        add_button.set_focus_on_click(False)
        add_button.set_border_width(constants.BUTTON_BORDER_WIDTH)
        add_button.set_size_request(constants.BUTTON_MIN_WIDTH, constants.BUTTON_MIN_HEIGHT)

        remove_button = gtk.Button('Remove')
        remove_button.set_focus_on_click(False)
        remove_button.set_border_width(constants.BUTTON_BORDER_WIDTH)
        remove_button.set_size_request(constants.BUTTON_MIN_WIDTH, constants.BUTTON_MIN_HEIGHT)

        self['add_button'] = add_button
        self['remove_button'] = remove_button

        self.Hbox = gtk.HBox()
        self.Hbox.pack_end(self['remove_button'], expand=False, fill=True)
        self.Hbox.pack_end(self['add_button'], expand=False, fill=True)

        scrollable = gtk.ScrolledWindow()
        scrollable.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scrollable.add(self.treeView['tree_view'])

        outcomes_label = gui_helper.create_label_with_text_and_spacing("OUTCOMES",
                                                                       letter_spacing=constants.LETTER_SPACING_1PT)
        outcomes_label.set_alignment(0.0, 0.5)
        eventbox = gtk.EventBox()
        eventbox.set_border_width(constants.BORDER_WIDTH_TEXTVIEW)
        eventbox.set_name('label_wrapper')
        eventbox.add(outcomes_label)
        title_viewport = gtk.Viewport()
        title_viewport.set_name("outcomes_title_wrapper")
        title_viewport.add(eventbox)

        self.vbox.pack_start(title_viewport, False, True, 0)
        self.vbox.pack_start(scrollable, True, True, 0)
        self.vbox.pack_start(self.Hbox, expand=False, fill=True)
        self.vbox.show_all()

        self['main_frame'] = self.vbox
        self['tree'] = self.tree

    def get_top_widget(self):
        return self.vbox
