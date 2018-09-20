
import os, sys, atexit, signal, time

import barbot.config

def _daemonize():
    try:
        pid = os.fork()
        if pid > 0:
            # exit first parent
            sys.exit(0)
    except OSError as e:
        sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
        sys.exit(1)

    # decouple from parent environment
    os.chdir("/")
    os.setsid()
    os.umask(0)

    # do second fork
    try:
        pid = os.fork()
        if pid > 0:
            # exit from second parent
            sys.exit(0)
    except OSError as e:
        sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
        sys.exit(1)

    # redirect standard file descriptors
    sys.stdout.flush()
    sys.stderr.flush()
    si = file('/dev/null', 'r')
    so = file('/dev/null', 'a+')
    se = file('/dev/null', 'a+', 0)
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())

    # write pidfile
    atexit.register(_deletePID)
    pid = str(os.getpid())
    file(getPIDFile(), 'w+').write("%s\n" % pid)

def _deletePID():
    os.remove(getPIDFile())
    
def start(main):
    pid = getDaemonPID()
    if pid:
        sys.stderr.write("pidfile %s already exist. Daemon already running?\n" % getPIDFile())
        sys.exit(1)
   
    # Start the daemon
    _daemonize()
    main()
 
def stop(section):
    pid = getDaemonPID()
    if not pid:
        sys.stderr.write("pidfile %s does not exist. Daemon not running?\n" % getPIDFile())
        return # not an error in a restart

    # Try killing the daemon process       
    try:
        while 1:
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.1)
    except OSError as err:
        err = str(err)
        if err.find('No such process') > 0:
            if os.path.exists(getPIDFile()):
                os.remove(getPIDFile())
        else:
            print(err)
            sys.exit(1)

def restart(main):
    stop()
    start(main)

def status():
    pid = getDaemonPID()
    if pid:
        sys.stdout.write("Daemon is running with PID %s.\n" % pid)
    else:
        sys.stdout.write("Daemon is not running.\n")
    
def getDaemonPID():
    try:
        pf = open(getPIDFile(), 'r')
        pid = int(pf.read().strip())
        pf.close()
    except IOError:
        pid = None
    return pid
    
def getPIDFile():
    return barbot.config.config.getpath('server', 'pidFile')