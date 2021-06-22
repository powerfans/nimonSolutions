# I.安装配置篇

# I.I 安装InfluxDB
# I.I.1 下载并安装InfluxDB
  首先下载InfluxDB(from https://www.power-devops.com/influxdb), 下载详细链接参考:soft_deps/download_links_for_方案1.md
  以1.8.6版本为例，在监控管理节点安装InfluxDB
  $ rpm -Uvh influxdb-1.8.6-1.el7.ppc64le.rpm
# I.I.2 配置InfluxDB
  InfluxDB缺省data和metadata存放在/var/lib/influxdb下，建议修改路,比如/data下:
  $ mkdir -p /data/meta /data/data /data/wal;  chown -R influxdb:influxdb /data/
  $ vi /etc/influxdb/influxdb.conf
    [meta]
    # Where the metadata/raft database is stored
    dir = "/data/meta"
    ...
    [data]
    ## The directory where the TSM storage engine stores TSM files.
    dir = "/data/data"
    ## The directory where the TSM storage engine stores WAL files.
    wal-dir = "/data/wal"
    ...
# I.I.3 启动InfluxDB
    $ systemctl start influxdb
    $ systemctl status -l influxdb
# I.I.4 创建数据库 nimon_aix, nimon_plinux, nimon_x86linux, nimon_hmc,分别用于收集AIX&VIOS,Linux on Power,Linux on X86, HMC性能监控数据
    $ influx
    > create database nimon_aix;
    > create database nimon_plinux;
    > create database nimon_x86linux;
    > create database nimon_hmc;
    > show databases;
	name: databases
	name
	----
	_internal
	nimon_aix
	nimon_hmc
	nimon_plinux
	nimon_x86linux
# I.I.4 创建InfluxDB用户
    # influx
    > create user "admin" with password 'n1M0nP0wd' with all privileges;
    > show users
	user  admin
	----  -----
	admin true
    > exit
    通过admin用户连接测试
    # influx -host localhost -port 8086 -username admin -password n1M0nP0wd
# I.I.4 启用InfluxDB认证
    $　vi /etc/influxdb/influxdb.conf
	[http]
	  # Determines whether HTTP endpoint is enabled.
	  # enabled = true
	  # Determines whether the Flux query endpoint is enabled.
	  # flux-enabled = false
	  # Determines whether the Flux query logging is enabled.
	  # flux-log-enabled = false
	  # The bind address used by the HTTP service.
	  # bind-address = ":8086"
	  # Determines whether user authentication is enabled over HTTP/HTTPS.
	  auth-enabled = true
     ##重启InfluxDB生效
     $ systemctl restart influxdb
    

# I.II 安装Grafana
# I.II.1 下载并安装Grafana
  首先下载Grafana(from https://www.power-devops.com/grafana), 下载详细链接参考:soft_deps/download_links_for_方案1.md
  以7.5.7版本为例，在监控管理节点安装Grafana
  $ rpm -Uvh grafana-7.5.7-1.el7.ppc64le.rpm
# I.II.2 启动并查验状态
    $ systemctl daemon-reload; systemctl start grafana-server
    $ systemctl status -l grafana-server
# I.II.3 登录Grafana，缺省用户/密码:admin/admin,缺省port:3000
    http://xxx.xxx.xxx.xxx:3000
    首次登录会提示更改密码,这里假定新密码为:gr@fanan1m0n
# I.II.4 安装需要的plugins
    目前需要如下3个plugins, 下载详细链接参考:soft_deps/download_links_for_方案1.md
    grafana-influxdb-flux-datasource
    grafana-piechart-panel
    grafana-clock-panel
    下载后解压并安装到/var/lib/grafana/plugins目录，示例（请注意版本不同会有差异）
    $ cd /var/lib/grafana/plugins
    $ unzip /root/soft_pkgs/grafana_plugins/grafana-influxdb-flux-datasource-v5.4.1-0-gfd7f150.zip 
    $ mv grafana-influxdb-flux-datasource-fd7f150 grafana-influxdb-flux-datasource
    $ unzip /root/soft_pkgs/grafana_plugins/grafana-piechart-panel-1.6.1.zip 
    $ unzip /root/soft_pkgs/grafana_plugins/grafana-clock-panel-v1.0.3-0-gbb466d0.zip
    $ mv grafana-clock-panel-bb466d0 grafana-clock-panel
    重启Grafana让插件生效
    $ systemctl restart  grafana-server
    如需别的组件，将继续补充

# I.II.5 在Grafana上配置数据源，添加DashBoard，告警方式和告警规则: 详见 《Nimon+InfluxDB+Prometheus+Grafana实现跨平台实时可视化监控-V1.0.doc》
    目前已有dashboard模板: 整机, AIX, VIOS, Linux for Power, Linux for X86, HMC
    参考:
    dashboards/10832_nimon按序列号整机监控_for_AIX_&_VIOS.json  
    dashboards/10891_nimon监控AIX分区.json
    dashboards/10892_nimon监控VIOS分区.json
    dashboards/10844-nimon监控Power_Linux分区.json              
    dashboards/10845-nimon监控X86_Linux分区.json  

    

# I.III 部署nimon监控, 采用crontab形式，每天重启一次，监控全天
    nimon可执行程序从https://tinyurl.com/njmon下载
    目前采用版本:
    AIX、VIOS: clients/nimon_zip/njmon_aix_binaries_v73.zip
    Linux for Power/X86: clients/nimon_zip/njmon_linux_binaries_v71.zip
    nimon监控脚本须调整设置如下参数
      Mon_Interval      ##监控采样间隔
      Mon_Count         ##监控采样次数
      InfluxDB_IP       ##InfluxDB 数据库IP
      InfluxDB_Port     ##InfluxDB 端口Port
      InfluxDB_User     ##InfluxDB 用户User
      InfluxDB_PWD      ##InfluxDB 用户密码
      InfluxDB_Database ##InfluxDB 数据库
    然后对监控脚本采用gzexe压缩加密，保护脚本中监控环境的明文配置信息
    假定将nimon监控脚本和zip包拷贝到/home/nimon目录下
# I.III.1 AIX部署
    $ unzip njmon_aix_binaries_v73.zip &&  sh ninstall
    $ chmod +x nimonRunOnAIX.sh
    $ crontab -e
      1 0 * * * /home/nimon/nimonRunOnAIX.sh 1>/dev/null 2>&1 
# I.III.2 VIOS部署
    $ unzip njmon_aix_binaries_v73.zip &&  sh ninstall
    $ chmod +x nimonRunOnVIOS.sh
    $ crontab -e
      5 0 * * * /home/nimon/nimonRunOnVIOS.sh 1>/dev/null 2>&1 
# I.III.3 Linux for Power部署
    $ unzip njmon_linux_binaries_v71.zip &&  sh ninstall
    $ chmod +x nimonRunOnPLinux.sh
    $ crontab -e
      15 0 * * * /home/nimon/nimonRunOnPLinux.sh 1>/dev/null 2>&1 
# I.III.4 Linux for X86部署
    $ unzip njmon_linux_binaries_v71.zip &&  sh ninstall
    $ chmod +x nimonRunOnX86Linux.sh
    $ crontab -e
      15 0 * * * /home/nimon/nimonRunOnX86Linux.sh 1>/dev/null 2>&1 
# I.III.5 HMC无需agent,只要对各台服务器开启性能收集即可

