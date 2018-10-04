# Copyright (C) 2015-2018 DLR
#
# All rights reserved. This program and the accompanying materials are made
# available under the terms of the Eclipse Public License v1.0 which
# accompanies this distribution, and is available at
# http://www.eclipse.org/legal/epl-v10.html
#
# Contributors:
# Franz Steinmetz <franz.steinmetz@dlr.de>
# Rico Belder <rico.belder@dlr.de>
# Sebastian Brunner <sebastian.brunner@dlr.de>

from gi.repository import Gtk
from gi.repository import GObject
from gtkmvc3 import View
from rafcon.gui.utils import constants


class HistoryTreeView(View, Gtk.TreeView):

    def __init__(self):
        View.__init__(self)
        GObject.GObject.__init__(self)

        foreground = 5

        tvcolumn = Gtk.TreeViewColumn('Nr', Gtk.CellRendererText(), text=1, foreground=foreground)
        tvcolumn.set_property("sizing", Gtk.TreeViewColumnSizing.AUTOSIZE)
        self.append_column(tvcolumn)

        tvcolumn = Gtk.TreeViewColumn('Action', Gtk.CellRendererText(), text=2, foreground=foreground)
        tvcolumn.set_property("sizing", Gtk.TreeViewColumnSizing.AUTOSIZE)
        self.append_column(tvcolumn)

        tvcolumn = Gtk.TreeViewColumn('Parameters', Gtk.CellRendererText(), text=7, foreground=foreground)
        tvcolumn.set_property("sizing", Gtk.TreeViewColumnSizing.AUTOSIZE)
        self.append_column(tvcolumn)

        tvcolumn = Gtk.TreeViewColumn('Affects', Gtk.CellRendererText(), text=3, foreground=foreground)
        tvcolumn.set_property("sizing", Gtk.TreeViewColumnSizing.AUTOSIZE)
        # tvcolumn.set_min_width(150)
        self.append_column(tvcolumn)

        self['history_treeview'] = self
        self.top = 'history_treeview'


class ModificationHistoryView(View, Gtk.ScrolledWindow):

    def __init__(self):
        View.__init__(self)
        GObject.GObject.__init__(self)

        history_tree = HistoryTreeView()
        history_tree.set_name('history_tree')

        undo_button = Gtk.Button("Undo")
        undo_button.set_border_width(constants.BUTTON_BORDER_WIDTH)
        redo_button = Gtk.Button("Redo")
        redo_button.set_border_width(constants.BUTTON_BORDER_WIDTH)
        reset_button = Gtk.Button("Reset")
        reset_button.set_border_width(constants.BUTTON_BORDER_WIDTH)
        branch_checkbox = Gtk.CheckButton("B")
        branch_checkbox.set_tooltip_text('Show branches')
        branch_checkbox.set_border_width(constants.BUTTON_BORDER_WIDTH)
        folded_checkbox = Gtk.CheckButton("F")
        folded_checkbox.set_tooltip_text('Fold branches')
        folded_checkbox.set_border_width(constants.BUTTON_BORDER_WIDTH)

        button_hbox = Gtk.HBox()
        button_hbox.pack_end(folded_checkbox, False, True, 0)
        button_hbox.pack_end(branch_checkbox, False, True, 0)
        button_hbox.pack_end(reset_button, False, True, 0)
        button_hbox.pack_end(redo_button, False, True, 0)
        button_hbox.pack_end(undo_button, False, True, 0)

        history_vbox = Gtk.VBox()
        history_vbox.pack_start(self, True, True, 0)
        history_vbox.pack_start(button_hbox, False, True, 0)

        self.add(history_tree)
        self.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.show_all()

        self['history_vbox'] = history_vbox
        self['history_view'] = self
        self['history_tree'] = history_tree
        self['undo_button'] = undo_button
        self['redo_button'] = redo_button
        self['reset_button'] = reset_button
        self['branch_checkbox'] = branch_checkbox
        self['folded_checkbox'] = folded_checkbox
        self.top = 'history_view'
