#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul 21 17:55:42 2025

@author: simonchang
"""
import sys
import traceback
import io
from contextlib import redirect_stdout, redirect_stderr
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QTextCursor


class PythonConsoleWidget(QTextEdit):
    """A Python console widget that behaves like a terminal"""
    
    def __init__(self, namespace=None, parent=None):
        super().__init__(parent)
        
        # Set up the console appearance
        self.setFont(QFont("Consolas", 10))  # Use monospace font
        self.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #555;
            }
        """)
        
        # Console state
        self.command_history = []
        self.history_index = -1
        self.current_command = ""
        self.prompt = ">>> "
        self.continuation_prompt = "... "
        self.in_continuation = False
        self.multiline_command = ""
        
        # Set up the namespace for code execution
        self.namespace = namespace or {}
        self._setup_default_namespace()
        
        # Initialize console
        self.initialize_console()
    
    def _setup_default_namespace(self):
        """Set up default namespace with built-in functions"""
        defaults = {
            '__name__': '__console__',
            '__doc__': None,
            'help': help,
            'dir': dir,
            'len': len,
            'print': print,
            'range': range,
            'list': list,
            'dict': dict,
            'str': str,
            'int': int,
            'float': float,
        }
        
        # Add defaults, but don't overwrite existing items
        for key, value in defaults.items():
            if key not in self.namespace:
                self.namespace[key] = value
    
    def add_to_namespace(self, name, obj):
        """Add an object to the console namespace"""
        self.namespace[name] = obj
    
    def initialize_console(self):
        """Initialize the console with welcome message and first prompt"""
        welcome_msg = f"Python Console (Python {sys.version_info.major}.{sys.version_info.minor})\n"
        welcome_msg += "Type 'help()' for help\n\n"
        
        self.append(welcome_msg)
        self.append_prompt()
    
    def append_prompt(self):
        """Add a prompt to the console"""
        prompt = self.continuation_prompt if self.in_continuation else self.prompt
        self.insertPlainText(prompt)
        self.moveCursor(QTextCursor.End)
    
    def keyPressEvent(self, event):
        """Handle key press events"""
        cursor = self.textCursor()
        
        # Handle special keys
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self.handle_enter()
            return
        elif event.key() == Qt.Key_Up:
            self.handle_history_up()
            return
        elif event.key() == Qt.Key_Down:
            self.handle_history_down()
            return
        elif event.key() == Qt.Key_Tab:
            # Simple tab completion could go here
            self.insertPlainText("    ")  # Insert 4 spaces for now
            return
        elif event.key() == Qt.Key_Backspace:
            # Prevent backspacing over the prompt
            if self.get_current_line_text().startswith(self.prompt) or \
               self.get_current_line_text().startswith(self.continuation_prompt):
                prompt_len = len(self.continuation_prompt if self.in_continuation else self.prompt)
                line_text = self.get_current_line_text()
                if len(line_text) <= prompt_len:
                    return
        
        # Allow normal text input only at the end
        if cursor.position() >= self.get_prompt_position():
            super().keyPressEvent(event)
    
    def get_current_line_text(self):
        """Get the text of the current line"""
        cursor = self.textCursor()
        cursor.select(QTextCursor.LineUnderCursor)
        return cursor.selectedText()
    
    def get_prompt_position(self):
        """Get the position where the prompt ends"""
        text = self.toPlainText()
        lines = text.split('\n')
        if not lines:
            return 0
        
        last_line = lines[-1]
        if last_line.startswith(self.prompt) or last_line.startswith(self.continuation_prompt):
            # Position after the prompt
            return len(text) - len(last_line) + len(self.continuation_prompt if self.in_continuation else self.prompt)
        return len(text)
    
    def get_current_command(self):
        """Extract the current command from the input line"""
        line_text = self.get_current_line_text()
        if line_text.startswith(self.prompt):
            return line_text[len(self.prompt):]
        elif line_text.startswith(self.continuation_prompt):
            return line_text[len(self.continuation_prompt):]
        return line_text
    
    def handle_enter(self):
        """Handle the Enter key press"""
        command = self.get_current_command()
        
        # Move to end and add newline for the command we just entered
        self.moveCursor(QTextCursor.End)
        self.insertPlainText('\n')
        
        if self.in_continuation:
            self.multiline_command += "\n" + command
            # Check if we should exit continuation mode
            if command.strip() == "":
                # Empty line in continuation mode - execute the multiline command
                self.execute_command(self.multiline_command)
                self.multiline_command = ""
                self.in_continuation = False
            else:
                # Continue with multiline input
                self.append_prompt()
        else:
            # Single line command
            if self.should_continue(command):
                # Start multiline mode
                self.multiline_command = command
                self.in_continuation = True
                self.append_prompt()
            else:
                # Execute single line command
                if command.strip():
                    self.execute_command(command)
                else:
                    self.append_prompt()
    
    def should_continue(self, command):
        """Check if the command should continue on the next line"""
        # Simple check for multiline constructs
        stripped = command.strip()
        if stripped.endswith(':'):
            return True
        
        # Check for unmatched brackets/parentheses
        brackets = {'(': ')', '[': ']', '{': '}'}
        stack = []
        in_string = False
        string_char = None
        
        for char in command:
            if char in ['"', "'"] and not in_string:
                in_string = True
                string_char = char
            elif char == string_char and in_string:
                in_string = False
                string_char = None
            elif not in_string:
                if char in brackets:
                    stack.append(char)
                elif char in brackets.values():
                    if stack and brackets[stack[-1]] == char:
                        stack.pop()
        
        return len(stack) > 0 or in_string
    
    def execute_command(self, command):
        """Execute a Python command"""
        if not command.strip():
            self.append_prompt()
            return
        
        # Add to command history
        if command.strip() not in self.command_history:
            self.command_history.append(command.strip())
        self.history_index = -1
        
        # Capture stdout and stderr
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        try:
            # Redirect output
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture
            
            # Try to compile and execute the command
            try:
                # First try to compile as an expression
                code = compile(command, '<console>', 'eval')
                result = eval(code, self.namespace)
                if result is not None:
                    print(repr(result))
            except SyntaxError:
                # If that fails, try as a statement
                try:
                    code = compile(command, '<console>', 'exec')
                    exec(code, self.namespace)
                except Exception as e:
                    self.handle_exception(e)
            except Exception as e:
                self.handle_exception(e)
                
        finally:
            # Restore stdout and stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr
        
        # Display any output
        stdout_text = stdout_capture.getvalue()
        stderr_text = stderr_capture.getvalue()
        
        if stdout_text:
            # Remove trailing newlines and add the text
            clean_output = stdout_text.rstrip('\n\r')
            if clean_output:
                self.insertPlainText(clean_output + '\n')
        if stderr_text:
            clean_error = stderr_text.rstrip('\n\r')
            if clean_error:
                self.insertPlainText(clean_error + '\n')
        
        self.append_prompt()
    
    def handle_exception(self, exception):
        """Handle and display exceptions"""
        error_msg = traceback.format_exc()
        print(error_msg, file=sys.stderr)
    
    def handle_history_up(self):
        """Handle up arrow key for command history"""
        if not self.command_history:
            return
        
        if self.history_index == -1:
            self.current_command = self.get_current_command()
            self.history_index = len(self.command_history) - 1
        else:
            self.history_index = max(0, self.history_index - 1)
        
        self.replace_current_command(self.command_history[self.history_index])
    
    def handle_history_down(self):
        """Handle down arrow key for command history"""
        if not self.command_history or self.history_index == -1:
            return
        
        self.history_index += 1
        if self.history_index >= len(self.command_history):
            self.history_index = -1
            self.replace_current_command(self.current_command)
        else:
            self.replace_current_command(self.command_history[self.history_index])
    
    def replace_current_command(self, new_command):
        """Replace the current command with a new one"""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        # Select from prompt to end of line
        line_text = self.get_current_line_text()
        prompt = self.continuation_prompt if self.in_continuation else self.prompt
        command_start = len(line_text) - len(line_text.split(prompt)[-1])
        
        cursor.movePosition(QTextCursor.StartOfLine)
        cursor.movePosition(QTextCursor.Right, QTextCursor.MoveAnchor, len(prompt))
        cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
        
        cursor.removeSelectedText()
        cursor.insertText(new_command)
        self.setTextCursor(cursor)
        
        