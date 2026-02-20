# Decorators for easier callback registration
def before_job(func):
    """Decorator to mark a function as a before_job callback"""
    func._callback_type = 'before_job'
    return func

def after_job(func):
    """Decorator to mark a function as an after_job callback"""
    func._callback_type = 'after_job'
    return func

def before_tenant(func):
    """Decorator to mark a function as a before_tenant callback"""
    func._callback_type = 'before_tenant'
    return func

def after_tenant(func):
    """Decorator to mark a function as an after_tenant callback"""
    func._callback_type = 'after_tenant'
    return func

def before_script(func):
    """Decorator to mark a function as a before_script callback"""
    func._callback_type = 'before_script'
    return func

def after_script(func):
    """Decorator to mark a function as an after_script callback"""
    func._callback_type = 'after_script'
    return func

def on_error(func):
    """Decorator to mark a function as an on_error callback"""
    func._callback_type = 'on_error'
    return func