	
	function switchViews(type){
		if($("#id_type").val() =="date"){
			$("#div_id_run_time_date").show();
			$("#div_id_run_time_interval").hide();
			$("#div_id_run_time_cron").hide();
		}
		if($("#id_type").val()=="interval"){
			$("#div_id_run_time_date").hide();
			$("#div_id_run_time_interval").show();
			$("#div_id_run_time_cron").hide();
		}
		if($("#id_type").val()=="cron"){
			$("#div_id_run_time_date").hide()
			$("#div_id_run_time_interval").hide();
			$("#div_id_run_time_cron").show();
			}
	}
	
     $(function (){
		$(".ui_timepicker").datetimepicker({
			showSecond: true,
			timeFormat: 'HH:mm:ss',
			stepHour: 1,
			stepMinute: 1,
			stepSecond: 1
		})
		$("#id_type").bind('change', function(){
			switchViews();
		});
		switchViews();
	})