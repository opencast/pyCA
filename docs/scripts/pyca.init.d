#!/bin/sh
#
# matterhorn   Start/Stop the Opencast Matterhorn system
#
# chkconfig:   - 60 40
# description: 

### BEGIN INIT INFO
# Provides: pyCA
# Required-Start: $local_fs $remote_fs $syslog $network
# Required-Stop:
# Default-Start:
# Default-Stop:
# Short-Description: run pyca
# Description: 
### END INIT INFO

pyca="python /opt/pyCA/pyca.py run"
prog="pyca"
logfile="/var/log/pyca.log"
pidfile="/var/run/${prog}.pid"

killdelay=7

# Load configuration files
[ -e /etc/sysconfig/$prog ] && . /etc/sysconfig/$prog

success() {
	printf "\r%-58s [\033[32m  OK  \033[0m]\n" "$1"
}

failed() {
	printf "\r%-58s [\033[31mFAILED\033[0m]\n" "$1"
}

start() {
	smsg="Starting $prog: "
	echo -n $smsg
    if [ -f $pidfile ] 
    then 
        rh_status
	else
	   # Start pyCA and create a pidfile
       $pyca >> $logfile & echo "$!" > $pidfile 
	   retval=$?
    fi
	[ $retval -eq 0 ] && success "$smsg" || failed "$smsg"
	return $retval
}

stop() {
	smsg="Stopping $prog: "
	echo -n $smsg
    pid="$(cat $pidfile)"
	kill $pid 
	retval=$?
	if [ $retval -eq 0 ]
	then
		rm -f $pidfile
		success "$smsg"
	else
		failed "$smsg"
	fi
	return $retval
}

restart() {
	stop
	start
}

reload() {
	restart
}

force_reload() {
	restart
}

rh_status() {
	# run checks to determine if the service is running or use generic status
#	if [ -f $lockfile ] && [ -f $pidfile ]
	if [ -f $pidfile ]
	then
		pid="$(cat $pidfile)"
		echo $"${prog} (pid $pid) is running..." 
		return 0
	fi
	echo "${prog} is stopped"
	return 3
}

rh_status_q() {
	rh_status >/dev/null 2>&1
}


case "$1" in
	start)
		rh_status_q && exit 0
		$1
		;;
	stop)
		rh_status_q || exit 0
		$1
		;;
	restart)
		$1
		;;
	reload)
		rh_status_q || exit 7
		$1
		;;
	force-reload)
		force_reload
		;;
	status)
		rh_status
		;;
	condrestart|try-restart)
		rh_status_q || exit 0
		restart
		;;
	*)
		echo $"Usage: $0 {start|stop|status|restart|condrestart|try-restart|reload|force-reload}"
		exit 2
esac
exit $?
