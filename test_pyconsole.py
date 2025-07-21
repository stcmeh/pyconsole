#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul 21 18:35:16 2025

@author: simonchang
"""

import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QLineEdit,
                             QSplitter, QTextEdit)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QTextCursor

from pyconsole import PythonConsoleWidget


class SharedAppState:
    """Shared state object that can be accessed from both the GUI and console"""
    def __init__(self):
        self.data = {}
        self.objects = {}
        self.callbacks = []  # List of functions to call when state changes
    
    def add_change_callback(self, callback):
        """Add a callback function that gets called when state changes"""
        self.callbacks.append(callback)
    
    def _notify_change(self, key, value):
        """Notify all callbacks about a state change"""
        for callback in self.callbacks:
            try:
                callback(key, value)
            except Exception as e:
                print(f"Error in state change callback: {e}")
    
    def set(self, key, value):
        """Set a value in shared state"""
        self.data[key] = value
        print(f"Set '{key}' = {repr(value)}")  # Add feedback
        self._notify_change(key, value)
        
    def get(self, key, default=None):
        """Get a value from shared state"""
        return self.data.get(key, default)
    
    def set_object(self, name, obj):
        """Store an object in shared state"""
        self.objects[name] = obj
    
    def get_object(self, name):
        """Get an object from shared state"""
        return self.objects.get(name)
    
    def __getitem__(self, key):
        """Allow dict-like access: app_state['key']"""
        return self.data[key]
    
    def __setitem__(self, key, value):
        """Allow dict-like assignment: app_state['key'] = value"""
        self.data[key] = value
        # Print confirmation when setting values
        print(f"Set '{key}' = {repr(value)}")
        self._notify_change(key, value)
    
    def __contains__(self, key):
        """Allow 'key in app_state' checks"""
        return key in self.data
    
    def keys(self):
        """Get all keys"""
        return self.data.keys()
    
    def values(self):
        """Get all values"""
        return self.data.values()
    
    def items(self):
        """Get all key-value pairs"""
        return self.data.items()
    
    def __repr__(self):
        """Better representation showing the data"""
        return f"SharedAppState(data={self.data}, objects={list(self.objects.keys())})"


class CADApplication(QMainWindow):
    """Main CAD application with integrated Python console"""
    
    def __init__(self):
        super().__init__()
        self.shared_state = SharedAppState()
        self.setup_ui()
        self.setup_shared_data()
    
    def setup_ui(self):
        """Set up the user interface"""
        self.setWindowTitle("CAD Application with Python Console")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        main_layout = QHBoxLayout(central_widget)
        
        # Create splitter for resizable panes
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Create CAD workspace (placeholder)
        workspace = self.create_workspace()
        splitter.addWidget(workspace)
        
        # Create console widget with initial namespace
        initial_namespace = {
            'app_state': self.shared_state
        }
        self.console = PythonConsoleWidget(namespace=initial_namespace)
        splitter.addWidget(self.console)
        
        # Set initial splitter sizes (70% workspace, 30% console)
        splitter.setSizes([700, 300])
    
    def create_workspace(self):
        """Create the main CAD workspace (placeholder)"""
        workspace = QWidget()
        layout = QVBoxLayout(workspace)
        
        # Title
        title = QLabel("CAD Workspace")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # Some example controls
        controls_layout = QHBoxLayout()
        
        # Input for testing shared state
        self.value_input = QLineEdit()
        self.value_input.setPlaceholderText("Enter a value...")
        controls_layout.addWidget(QLabel("Test Value:"))
        controls_layout.addWidget(self.value_input)
        
        # Button to set shared state
        set_button = QPushButton("Set in Shared State")
        set_button.clicked.connect(self.set_shared_value)
        controls_layout.addWidget(set_button)
        
        layout.addLayout(controls_layout)
        
        # Add a live state summary
        state_label = QLabel("Shared State:")
        state_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(state_label)
        
        self.state_summary = QTextEdit()
        self.state_summary.setMaximumHeight(100)
        self.state_summary.setStyleSheet("background-color: #f0f0f0; font-family: monospace;")
        layout.addWidget(self.state_summary)
        
        # Info display
        info_label = QLabel("Activity Log:")
        info_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(info_label)
        
        self.info_display = QTextEdit()
        self.info_display.setMaximumHeight(200)
        self.info_display.setPlainText("Shared state interactions will appear here...")
        layout.addWidget(self.info_display)
        
        layout.addStretch()  # Push everything to top
        
        return workspace
    
    def setup_shared_data(self):
        """Set up some initial shared data"""
        self.shared_state.set('app_name', 'CAD Application')
        self.shared_state.set('version', '1.0')
        self.shared_state.set_object('main_window', self)
        
        # Register for state change notifications
        self.shared_state.add_change_callback(self.on_state_changed)
        
        # Initialize the state summary display
        self.update_state_summary()
        
        # Add some useful functions to the console namespace
        self.console.add_to_namespace('update_info', self.update_info_display)
        self.console.add_to_namespace('get_input_value', lambda: self.value_input.text())
        self.console.add_to_namespace('set_input_value', lambda v: self.value_input.setText(str(v)))
        self.console.add_to_namespace('show_shared_state', self.show_shared_state)
        self.console.add_to_namespace('refresh_gui', self.refresh_gui_from_state)
    
    def set_shared_value(self):
        """Set a value in shared state from the GUI"""
        value = self.value_input.text()
        if value:
            self.shared_state.set('gui_input', value)
            self.update_info_display(f"Set 'gui_input' to: {value}")
    
    def update_info_display(self, message):
        """Update the info display"""
        current = self.info_display.toPlainText()
        new_text = f"{current}\n{message}"
        self.info_display.setPlainText(new_text)
        
        # Scroll to bottom
        cursor = self.info_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.info_display.setTextCursor(cursor)
    
    def show_shared_state(self):
        """Display current shared state"""
        state_info = "Current Shared State:\n"
        state_info += f"Data: {dict(self.shared_state.data)}\n"
        state_info += f"Objects: {list(self.shared_state.objects.keys())}"
        self.update_info_display(state_info)
        return self.shared_state
    
    def refresh_gui_from_state(self):
        """Refresh GUI elements based on shared state"""
        gui_input = self.shared_state.get('gui_input', '')
        if gui_input != self.value_input.text():
            self.value_input.setText(gui_input)
            self.update_info_display(f"GUI updated from shared state: gui_input = '{gui_input}'")
    
    def on_state_changed(self, key, value):
        """Called automatically when shared state changes"""
        self.update_info_display(f"🔄 State changed: {key} = {repr(value)}")
        
        # Auto-update specific GUI elements based on key
        if key == 'gui_input':
            self.value_input.setText(str(value))
        elif key == 'app_title':
            self.setWindowTitle(str(value))
        
        # Update the current state display
        self.update_state_summary()
    
    def update_state_summary(self):
        """Update the live state summary display"""
        summary = "Data:\n"
        for key, value in self.shared_state.data.items():
            summary += f"  {key}: {repr(value)}\n"
        summary += f"\nObjects: {list(self.shared_state.objects.keys())}"
        self.state_summary.setPlainText(summary)


def main():
    app = QApplication(sys.argv)
    
    # Create and show the main window
    window = CADApplication()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
