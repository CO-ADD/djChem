

update coadd.act_struct_dr a
set pub_status = c.pub_status
from coadd.compound c
where a.structure_id = c.structure_id 

update coadd.act_ c
set pub_status = p.pub_status
from coadd.compound c
where p.project_id = c.project_id 
  and c.pub_status is Null


select act.structure_id, act.act_score_ave, act.pscore_ave,
 		act.result_type, act.assay_id, ass.assay_code, 
 		act.n_assays, act.result_min, act.result_median, act.result_max, act.result_unit, 
 		act.result_std_geomean, act.result_std_unit, act.inhibit_max_ave  
from coadd.act_struct_dr act 
 left join coadd.compound c on c.structure_id = act.structure_id
  left join coadd.project p on p.project_id = c.project_id
 left join coadd.assay ass on ass.assay_id = act.assay_id
where p.pub_status = 'Public' and act.source_id = 'SRC0001' 