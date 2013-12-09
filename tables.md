## task ##
- id
- name
- trigger
- script
 
## script ##
- id
- type
- group
- script
  
## task ##
- id
- script_id
- trigger
- 
## job ##
- id
- status paused|running|finished
- task_id 
- ip

script (1) -> task (n) 
task(1) -> job(n)

# 难点
    1. 写时冗余还是查询联表? 写时冗余意味着更新的时候要仔细保持一致性, 查询联表会不会影响效率，更新的时候会不会不方便
    2. 如何维持存储的分离和job_store的集中
    3. 汇报如何写入
    > 直接写入汇报日志队列， 汇报线程读取日志后写入mysql
    4. 立即运行job，是否影响原先的scheduler, 是否要汇报结果? 
    > 简单策略，不影响，不汇报。 成功简单提示成功即可，失败最好将失败原因显示出来。
    5. 如何防止多线程程序崩溃。
    > 两个外部连接, 防止中断
        - mysql 读取job，写入job状态
        - redis 读取队列，写入日志队列
    > 一个外部运行机制
        - 任务运行。 不可知。
        - 任务超时。怎么办
    6. 监控线程
    >   1. 进程是否崩溃
    >   2. 更新队列长度
    >   3. 
    
    7. 异常点
        * init
            - load_jobs
        * runtime:
            - get_job √
            - pop_change √ 
            - put_status
            - pop_status
            - report status
            - compute_next_run_time √
            - run √
        * 服务器
            - 内存、cpu等占用过高怎么办。 
            - job 运行超时怎么办. 
            - 是否有可能限制单个job，占用的cpu、内存、网络、时间等资源
    8. 监控线程
        - 发心跳包 (中心进程监控进程是否崩溃。 可以通过pid文件重启？)
        - 发cpu、内存等资源
        - job同步队列、和status日志队列长度
        - 当前的线程池 数量 、空限度等等


load_jobs:
    select * from task_dist d left join task a on task.id = task_dist.id where d.ip = '$ip' and status='normal'
get_job:
    select d.id, d.script_id, a.name, a.trigger,   from task_dist d left join task a on d.task_id = a.id and d.id = '$id'
    select * from script where id=script_id
add task:
    create script
    create task with script_id
    deploy task with task_id
update: 
    update trigger
    update other
delete:
    pass  
pause dist:
    pause 
run dist:
    pause

