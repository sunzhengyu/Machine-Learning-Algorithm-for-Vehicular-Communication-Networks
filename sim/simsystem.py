'''
This module provides `SimSystem` class which is used for simulation system control. 
`SimSystem` is a static class, it should be called directly without an instance.

It is used for:

- reporting simulation warning due to incorrect implementation
- stopping simulation due to a critical error

Note
----
SimSystem.err.message(err_str)
    Call this function when a fatal error has occured. Calling this 
    function will stop the running and report the provided error message.
SimSystem.warn.message(warn_str)
    Call this function when a non-critical situation has occured. Calling this 
    function will show a warning on the terminal but will not stop the running.
SimSystem.warn.no_implementation(inspect.stack()[0][3],self)
    Call this function to throw a warning in a virtual method.
    This will not stop the running, a warning will be shown and the 
    program will continue to run. Use this function in a virtual method
    to warn that a virtual method may not have implemented in a subclass.
'''
import warnings

class SimSystem:
    '''
    It is a `static` simulation system control class which is 
    used for others to throw warning or error. Warning will not stop the
    simulation but error will stop the running immediately.
    '''

    class err:
        '''For error.'''
        @staticmethod
        def message(err_str):
            '''Throw an error message and stop the running.
            
            Parameters
            ----------
            err_str : str
                The error message to show on the terminal.
            '''
            raise Exception(err_str)

    class warn:
        '''For warning.'''

        @staticmethod
        def message(warn_str):
            '''Throw a warning message.
            
            Parameters
            ----------
            warn_str : str
                The warning message to show on the terminal.
            '''
            warnings.warn(warn_str)

        @staticmethod
        def no_implementation(method_name, obj_name):
            '''Throw a warning message for no reimplementation of a
            virtual method in a subclass, but continue to run the program.

            This is a static method that should be called directly.
            This function should be called in a virtual method that 
            expect reimplementation, but may not cause a fatal error
            if executed. Usage:

            - `SimSystem.warn.no_implementation(inspect.stack()[0][3],self)`
            
            Parameters
            ----------
            module_name : str
                To provide the name of the virtual method that is being 
                executed.
            obj_name : str
                To provide the module that contains the virtual method.
            '''
            warn_str = "%s() virtual method is used for %s"%(method_name,obj_name) + \
                    " forget to reimplement the method?"
            warnings.warn(warn_str)


