(get_domain id_bgrat id_shost str__w)
(creds id_bgrat id_shost id_adomain)
(get_computers id_bgrat id_adomain)
(net_use id_bgrat id_shost id_zhost str__bd id_ddomaincredential str__e id_cdomainuser str__james id_adomain str__alpha id_bkshare)
(get_admin id_bgrat id_zhost id_adomain)
(smb_copy id_bgrat id_shost str__bh id_bkshare id_shost id_zhost whatever id_bmfile)
(wmic id_bgrat id_shost id_zhost id_bmfile somepath id_ddomaincredential id_cdomainuser id_adomain str__alpha str__e id_birat)
; cost = 7 (unit cost)
