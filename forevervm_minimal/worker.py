# worker.py

import pickle
import time
import threading
import os
import io
import sys
import traceback

class Worker:
    def __init__(self):
        # We'll store the environment as a dictionary (like 'globals()')
        # that the user code interacts with
        self.env = {}
    
    def execute_code(self, code):
        # Execute code in self.env context and capture stdout
        old_stdout = sys.stdout
        redirected_output = io.StringIO()
        sys.stdout = redirected_output
        
        result = None
        
        try:
            # Try to compile as an expression first
            try:
                compiled_code = compile(code, "<string>", "eval")
                result = eval(compiled_code, self.env)
            except SyntaxError:
                # If it's not an expression, compile as a statement
                compiled_code = compile(code, "<string>", "exec")
                exec(compiled_code, self.env)
            
            # Get the stdout output
            output = redirected_output.getvalue()
            
            # If there was a result from eval, add it to the output
            if result is not None:
                if output and not output.endswith('\n'):
                    output += '\n'
                output += f"Result: {result}\n"
            
            return f"Output:\n{output}" if output else "No output"
        
        except Exception as e:
            # Get the traceback
            error_traceback = traceback.format_exc()
            return f"Error:\n{error_traceback}"
        
        finally:
            # Restore stdout
            sys.stdout = old_stdout
    
    def serialize_environment(self):
        # Convert self.env into a pickle/dill
        # We can store only the parts we want
        return pickle.dumps(self.env)
    
    def restore_environment(self, pickled_env):
        # Unpickle into self.env
        self.env = pickle.loads(pickled_env)
    
    def terminate(self):
        # If we had an external container, we'd do `docker stop` or similar
        pass