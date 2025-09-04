# Gunicorn configuration for optimal performance and reduced resource usage
bind = "0.0.0.0:5000"
workers = 1
worker_class = "sync"
timeout = 60
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
preload_app = True
reload = False
worker_connections = 1000
reuse_port = True

# Reduce logging noise - set to error level to minimize WINCH signal logs
accesslog = None
errorlog = "-"
loglevel = "error"
access_log_format = '%(h)s "%(r)s" %(s)s %(b)s'

# Process naming
proc_name = "multi-agent-demo"