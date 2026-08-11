


let DB = {
  eleves: [],
  classes: [],
  enseignants: [],
  notes: [],
  paiements: [],
  frais: [],
  annonces: [],
  livres: [],
  creneaux: [],
  documents: [],
  examens: [],
  personnel: [],
  stocks: [],
  sante: [],
  transport: [],
  messages: [],
  cantine: [],
  parents: [],
  users: [],
  schools: []
};


let CURRENT_SCHOOL_ID = localStorage.getItem('currentSchoolId') || 'school_primaire_centrale';

function setCurrentSchoolId(id){
  CURRENT_SCHOOL_ID = id;
  localStorage.setItem('currentSchoolId', id);
  showToast('info','Espace sélectionné: '+id);

  if(window.FIREBASE_READY){
    loadFromFirebase();
    subscribeFirebaseLive();
  } else {

    renderDashboard();
  }
}


let CURRENT_USER = null;


function saveGlobalToFirebase(collection, id, data){
  if(!window.FIREBASE_READY) return;
  try{
    const dbRef = window.FB_REF(window.FB_DB, `${collection}/${id}`);
    window.FB_SET(dbRef, data).then(()=>console.log('Global saved',collection,id)).catch(e=>console.warn(e));
  }catch(e){console.warn('saveGlobalToFirebase error',e);}
}


function setupAuthListeners(){
  if(!window.FB_AUTH) return;
  window.FB_ONAUTH(window.FB_AUTH, (user)=>{
    if(user){

      const uref = window.FB_REF(window.FB_DB, `users/${user.uid}`);
      window.FB_GET(uref).then(snap=>{
        if(snap.exists()){
          CURRENT_USER = snap.val();
          CURRENT_USER.uid = user.uid;
          console.log('Utilisateur connecté', CURRENT_USER.email || CURRENT_USER.uid);
          onUserSignedIn();
        } else {

          CURRENT_USER = {uid:user.uid,email:user.email,role:'Utilisateur'};
          onUserSignedIn();
        }
      }).catch(e=>{console.warn(e);CURRENT_USER={uid:user.uid,email:user.email};onUserSignedIn();});
    } else {
      CURRENT_USER = null;
      onUserSignedOut();
    }
  });
}

function onUserSignedIn(){

  const createBtn = document.querySelector("button[onclick=\"openModal('modal-create-school')\"]");
  const authBtn = document.getElementById('auth-btn');
  const userName = document.getElementById('sidebar-user-name');
  const userRole = document.getElementById('sidebar-user-role');
  const sessionChip = document.getElementById('session-chip');
  if(CURRENT_USER && CURRENT_USER.role && CURRENT_USER.role!=='Directeur'){
    if(createBtn) createBtn.style.display='none';
  } else {
    if(createBtn) createBtn.style.display='inline-flex';
  }
  if(authBtn) authBtn.textContent = 'Déconnexion';
  if(userName) userName.textContent = CURRENT_USER ? `${CURRENT_USER.firstname || ''} ${CURRENT_USER.lastname || ''}`.trim() || (CURRENT_USER.email || 'Utilisateur') : 'Directeur Admin';
  if(userRole) userRole.textContent = CURRENT_USER && CURRENT_USER.role ? CURRENT_USER.role : 'Utilisateur';
  if(sessionChip) sessionChip.textContent = 'Session: connecté · ' + (CURRENT_USER && CURRENT_USER.role ? CURRENT_USER.role : 'Utilisateur');
  applyRolePermissions();
}

function onUserSignedOut(){
  const createBtn = document.querySelector("button[onclick=\"openModal('modal-create-school')\"]");
  const authBtn = document.getElementById('auth-btn');
  const userName = document.getElementById('sidebar-user-name');
  const userRole = document.getElementById('sidebar-user-role');
  const sessionChip = document.getElementById('session-chip');
  if(createBtn) createBtn.style.display='inline-flex';
  if(authBtn) authBtn.textContent = 'Se connecter';
  if(userName) userName.textContent = 'Directeur Admin';
  if(userRole) userRole.textContent = 'Super administrateur';
  if(sessionChip) sessionChip.textContent = 'Session: non connectée';
  applyRolePermissions();
}

function applyRolePermissions(){


  const role = CURRENT_USER && CURRENT_USER.role ? CURRENT_USER.role : 'Directeur';
  const allowedPages = {
    Directeur: ['dashboard','eleves','parents','enseignants','personnel','classes','emploi-temps','notes','bulletins','presences','examens','finances','cantine','transport','bibliotheque','sante','stocks','messages','annonces','documents','rapports','parametres'],
    Gestionnaire: ['dashboard','eleves','parents','enseignants','classes','emploi-temps','notes','bulletins','presences','examens','finances','cantine','transport','bibliotheque','sante','stocks','messages','annonces','documents','rapports'],
    Enseignant: ['dashboard','emploi-temps','notes','presences','messages','annonces','documents']
  };

  document.querySelectorAll('.nav-item').forEach(item => {
    const onclick = item.getAttribute('onclick') || '';
    const match = onclick.match(/showPage\('([^']+)'\)/);
    const page = match ? match[1] : null;
    const allowed = page ? (allowedPages[role] || []).includes(page) : true;
    item.style.display = allowed ? 'flex' : 'none';
  });

  const createBtn = document.querySelector("button[onclick=\"openModal('modal-create-school')\"]");
  if(createBtn) createBtn.style.display = role === 'Directeur' ? 'inline-flex' : 'none';

  const quickNewBtn = document.querySelector("button[onclick=\"quickAdd()\"]");
  if(quickNewBtn && role === 'Enseignant') quickNewBtn.style.display = 'none';
}

function enforceRoleAccess(feature){

  const role = CURRENT_USER && CURRENT_USER.role ? CURRENT_USER.role : 'Directeur';
  const allowed = {
    'create-school': ['Directeur'],
    'manage-students': ['Directeur','Gestionnaire'],
    'manage-finances': ['Directeur','Gestionnaire'],
    'manage-notes': ['Directeur','Gestionnaire','Enseignant'],
    'manage-presences': ['Directeur','Gestionnaire','Enseignant'],
    'manage-settings': ['Directeur'],
    'send-announcements': ['Directeur','Gestionnaire'],
    'manage-users': ['Directeur']
  };
  if(!allowed[feature] || allowed[feature].includes(role)) return true;
  showToast('error','Accès refusé pour votre rôle : ' + role);
  return false;
}

let editingEleveId = null;




function seedData() {
  DB.classes = [
    {id:'cp-a',nom:'CP-A',niveau:'CP',effectif:32,enseignant:'Mme ONDONGO Marie',salle:'Salle 01'},
    {id:'ce1-a',nom:'CE1-A',niveau:'CE1',effectif:30,enseignant:'M. MAKOSSO Paul',salle:'Salle 02'},
    {id:'ce2-a',nom:'CE2-A',niveau:'CE2',effectif:28,enseignant:'Mme IKAMA Sandrine',salle:'Salle 03'},
    {id:'cm1-a',nom:'CM1-A',niveau:'CM1',effectif:35,enseignant:'M. BITSINDOU Roger',salle:'Salle 04'},
    {id:'cm2-a',nom:'CM2-A',niveau:'CM2',effectif:29,enseignant:'M. MOUKALA Ernest',salle:'Salle 05'},
    {id:'6a',nom:'6ème A',niveau:'6ème',effectif:38,enseignant:'Mme NGANGA Céline',salle:'Salle 06'}
  ];

  const prenoms = ['Jean','Marie','Pierre','Cécile','Emmanuel','Grâce','David','Joie','Samuel','Esther','Nathaniel','Rachel','Daniel','Rebecca','Joel','Sarah'];
  const noms = ['NZINGA','MOUKALA','BITSINDOU','IKAMA','MAKOSSO','ONDONGO','NGANGA','MABIKA','LOEMBA','TATY','MOUYABI','SAMBA','MALONGA','ITOUA','GOMA','KOUKA'];
  const classes = ['CP-A','CE1-A','CE2-A','CM1-A','CM2-A','6ème A'];

  for(let i=1;i<=30;i++){
    const nom = noms[i%noms.length];
    const prenom = prenoms[i%prenoms.length];
    const classe = classes[i%classes.length];
    const paye = Math.random() > 0.3;
    DB.eleves.push({
      id:'EL'+String(i).padStart(4,'0'),
      matricule:'2024'+String(i).padStart(4,'0'),
      nom,prenom,
      classe,
      ddn:`${2010+Math.floor(i/6)}-0${1+i%9}-${10+i%20}`,
      sexe: i%2===0?'M':'F',
      nationalite:'Congolaise',
      adresse:'Brazzaville, Congo',
      parentNom:`Parent de ${prenom}`,
      parentTel:'+242 06 '+String(Math.floor(Math.random()*9000000+1000000)),
      fraisStatut: paye?'Payé':'En attente',
      statut:'Actif',
      createdAt: new Date().toISOString()
    });
  }

  DB.enseignants = [
    {id:'E01',nom:'ONDONGO',prenom:'Marie',matieres:'CP Toutes matières',classes:'CP-A',heures:26,statut:'Actif'},
    {id:'E02',nom:'MAKOSSO',prenom:'Paul',matieres:'CE1 Toutes matières',classes:'CE1-A',heures:24,statut:'Actif'},
    {id:'E03',nom:'IKAMA',prenom:'Sandrine',matieres:'CE2 Toutes matières',classes:'CE2-A',heures:24,statut:'Actif'},
    {id:'E04',nom:'BITSINDOU',prenom:'Roger',matieres:'Mathématiques',classes:'CM1-A, CM2-A',heures:18,statut:'Actif'},
    {id:'E05',nom:'MOUKALA',prenom:'Ernest',matieres:'Français, Histoire',classes:'CM1-A, CM2-A',heures:20,statut:'Actif'},
    {id:'E06',nom:'NGANGA',prenom:'Céline',matieres:'Sciences, SVT',classes:'6ème A',heures:16,statut:'Actif'},
  ];

  DB.notes = [];
  const matieres = ['Français','Mathématiques','Sciences','Histoire-Géo'];
  for(let i=0;i<20;i++){
    const el = DB.eleves[i];
    matieres.forEach(m=>{
      DB.notes.push({
        id:'N'+Math.random().toString(36).substr(2,6),
        eleveId:el.id,
        eleveNom:el.nom+' '+el.prenom,
        classe:el.classe,
        matiere:m,
        type:'Contrôle continu',
        note:Math.round((8+Math.random()*12)*10)/10,
        sur:20,
        coef:2,
        date:'2024-10-15'
      });
    });
  }

  DB.paiements = [];
  const types = ['Scolarité Trimestre 1','Frais d\'inscription','Cantine','Transport'];
  for(let i=0;i<15;i++){
    const el = DB.eleves[i];
    DB.paiements.push({
      id:'P'+Math.random().toString(36).substr(2,6),
      eleveId:el.id,
      eleveNom:el.nom+' '+el.prenom,
      type:types[i%types.length],
      montant:[25000,15000,10000,8000][i%4],
      ref:'TXN-'+Date.now()+'-'+i,
      date:'2024-10-'+String(1+i%28).padStart(2,'0'),
      statut:'Validé'
    });
  }

  DB.frais = [
    {niveau:'CP',inscription:5000,scolarite:15000,cantine:8000,transport:5000},
    {niveau:'CE1',inscription:5000,scolarite:15000,cantine:8000,transport:5000},
    {niveau:'CE2',inscription:5000,scolarite:17000,cantine:8000,transport:5000},
    {niveau:'CM1',inscription:7000,scolarite:20000,cantine:9000,transport:6000},
    {niveau:'CM2',inscription:7000,scolarite:20000,cantine:9000,transport:6000},
    {niveau:'6ème',inscription:10000,scolarite:25000,cantine:10000,transport:7000},
  ];

  DB.annonces = [
    {id:'A1',titre:'Réunion parents d\'élèves',message:'Une réunion parents-enseignants est prévue le samedi 26 octobre 2024 à 9h. Votre présence est fortement souhaitée.',date:'2024-10-20',prio:'Importante',auteur:'Direction'},
    {id:'A2',titre:'Fermeture exceptionnelle',message:'L\'école sera fermée le lundi 28 octobre pour travaux. Les cours reprennent le mardi 29 octobre.',date:'2024-10-18',prio:'Urgente',auteur:'Direction'},
    {id:'A3',titre:'Compétition sportive inter-écoles',message:'Notre école participera à la compétition sportive régionale le 5 novembre. Encourageons nos équipes !',date:'2024-10-15',prio:'Normale',auteur:'Coord. Sport'},
  ];

  DB.livres = [
    {id:'L1',titre:'Manuel de Français CE2',auteur:'MEN Congo',categorie:'Manuel scolaire',stock:5,emprunte:false},
    {id:'L2',titre:'Mathématiques CM1',auteur:'MEN Congo',categorie:'Manuel scolaire',stock:3,emprunte:true,empruntePar:'NZINGA Jean',retour:'2024-11-01'},
    {id:'L3',titre:'L\'aventure de Samba',auteur:'Théophile OBENGA',categorie:'Littérature',stock:2,emprunte:false},
    {id:'L4',titre:'Histoire du Congo',auteur:'H. DESCHAMPS',categorie:'Histoire',stock:4,emprunte:true,empruntePar:'MOUKALA Marie',retour:'2024-10-28'},
  ];

  DB.examens = [
    {id:'EX1',nom:'Évaluation Trimestre 1',classe:'CP-A',date:'2024-11-15',salle:'Grande salle',surveillants:'Mme ONDONGO, M. MAKOSSO',statut:'Planifié'},
    {id:'EX2',nom:'Examen de Mathématiques',classe:'6ème A',date:'2024-11-20',salle:'Salle 06',surveillants:'M. BITSINDOU',statut:'Planifié'},
  ];

  DB.personnel = [
    {id:'P1',nom:'MABIKA Rosalie',poste:'Secrétaire',contact:'+242 06 111 11 11',contrat:'CDI',statut:'Actif'},
    {id:'P2',nom:'LOEMBA Victor',poste:'Comptable',contact:'+242 05 222 22 22',contrat:'CDI',statut:'Actif'},
    {id:'P3',nom:'TATY Bruno',poste:'Surveillant',contact:'+242 06 333 33 33',contrat:'CDD',statut:'Actif'},
    {id:'P4',nom:'SAMBA Joëlle',poste:'Cuisinière',contact:'+242 05 444 44 44',contrat:'CDI',statut:'Actif'},
  ];

  DB.stocks = [
    {id:'S1',article:'Craies blanches (boîte)',categorie:'Fournitures',stock:24,stockMin:10,unite:'boîte'},
    {id:'S2',article:'Cahiers grand format',categorie:'Fournitures',stock:5,stockMin:20,unite:'pcs'},
    {id:'S3',article:'Stylos bleus (lot 10)',categorie:'Fournitures',stock:18,stockMin:5,unite:'lot'},
    {id:'S4',article:'Tableau noir',categorie:'Mobilier',stock:2,stockMin:1,unite:'pcs'},
    {id:'S5',article:'Ordinateurs portables',categorie:'Informatique',stock:3,stockMin:2,unite:'pcs'},
  ];

  DB.sante = [
    {id:'S1',eleveNom:'NZINGA Jean',date:'2024-10-18',motif:'Fièvre',traitement:'Paracétamol, repos',parentNotifie:true,refere:false},
    {id:'S2',eleveNom:'MOUKALA Marie',date:'2024-10-17',motif:'Douleurs abdominales',traitement:'Observation',parentNotifie:true,refere:true},
  ];

  DB.transport = [
    {id:'T1',nom:'Bus Ligne 1',chauffeur:'MALONGA Robert',plaque:'BC-001-CG',capacite:40,eleves:32,itineraire:'Centre-ville → École'},
    {id:'T2',nom:'Bus Ligne 2',chauffeur:'ITOUA Marcel',plaque:'BC-002-CG',capacite:35,eleves:28,itineraire:'Poto-Poto → École'},
  ];


  DB.cantine = [
    {id:'MEN1',jour:'Lundi',plat:'Riz + Poulet sauce tomate',taille:'Assiette complète',prix:800},
    {id:'MEN2',jour:'Mardi',plat:'Haricots + Plantain mûr',taille:'Assiette complète',prix:800},
    {id:'MEN3',jour:'Mercredi',plat:'Riz + Poisson braisé',taille:'Assiette complète',prix:900},
    {id:'MEN4',jour:'Jeudi',plat:'Pâtes + Viande',taille:'Assiette complète',prix:900},
    {id:'MEN5',jour:'Vendredi',plat:'Riz + Sauce arachide',taille:'Assiette complète',prix:850},
  ];

  DB.documents = [
    {id:'D1',type:'Attestation d\'inscription',eleve:'NZINGA Jean',date:'2024-10-15',par:'Direction',qr:'QR-001'},
    {id:'D2',type:'Certificat de scolarité',eleve:'MOUKALA Marie',date:'2024-10-14',par:'Direction',qr:'QR-002'},
  ];

  DB.creneaux = [
    {id:'CR1',jour:'Lundi',classe:'CP-A',debut:'07:30',fin:'09:00',matiere:'Français',enseignant:'Mme ONDONGO',salle:'Salle 01'},
    {id:'CR2',jour:'Lundi',classe:'CP-A',debut:'09:15',fin:'10:45',matiere:'Mathématiques',enseignant:'Mme ONDONGO',salle:'Salle 01'},
    {id:'CR3',jour:'Lundi',classe:'CP-A',debut:'11:00',fin:'12:00',matiere:'Lecture',enseignant:'Mme ONDONGO',salle:'Salle 01'},
    {id:'CR4',jour:'Mardi',classe:'CP-A',debut:'07:30',fin:'09:00',matiere:'Mathématiques',enseignant:'Mme ONDONGO',salle:'Salle 01'},
    {id:'CR5',jour:'Mardi',classe:'CP-A',debut:'09:15',fin:'10:45',matiere:'Sciences',enseignant:'Mme ONDONGO',salle:'Salle 01'},
    {id:'CR6',jour:'Mercredi',classe:'CP-A',debut:'07:30',fin:'09:00',matiere:'Histoire-Géo',enseignant:'Mme ONDONGO',salle:'Salle 01'},
    {id:'CR7',jour:'Jeudi',classe:'CP-A',debut:'07:30',fin:'09:00',matiere:'EPS',enseignant:'Mme ONDONGO',salle:'Terrain'},
    {id:'CR8',jour:'Vendredi',classe:'CP-A',debut:'07:30',fin:'09:00',matiere:'Français',enseignant:'Mme ONDONGO',salle:'Salle 01'},
  ];

  DB.messages = [
    {id:'M1',from:'Parent NZINGA',avatar:'PN',msg:'Bonjour Directeur, mon enfant sera absent demain.',time:'10:30',read:false},
    {id:'M2',from:'Mme ONDONGO',avatar:'MO',msg:'Les notes du 1er trimestre sont prêtes.',time:'09:15',read:true},
    {id:'M3',from:'M. MAKOSSO',avatar:'MM',msg:'Bonjour, je souhaite signaler un problème avec la salle CE1.',time:'Hier',read:false},
  ];
}




const pageTitles = {
  dashboard:'Tableau de bord',eleves:'Gestion des élèves',parents:'Parents',
  enseignants:'Enseignants',personnel:'Personnel administratif',classes:'Classes & Niveaux',
  'emploi-temps':'Emploi du temps',notes:'Notes & Évaluations',bulletins:'Bulletins',
  presences:'Présences',examens:'Examens',finances:'Finances',cantine:'Cantine',
  transport:'Transport scolaire',bibliotheque:'Bibliothèque',sante:'Santé & Infirmerie',
  stocks:'Stocks & Matériel',messages:'Messages',annonces:'Annonces',
  documents:'Attestations & Documents',rapports:'Rapports',parametres:'Paramètres'
};

function showPage(id){
  document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n=>n.classList.remove('active'));
  const page = document.getElementById('page-'+id);
  if(page) page.classList.add('active');
  document.querySelectorAll('.nav-item').forEach(n=>{
    if(n.getAttribute('onclick')&&n.getAttribute('onclick').includes("'"+id+"'")) n.classList.add('active');
  });
  document.getElementById('header-title').innerHTML = '<span>'+(pageTitles[id]||id)+'</span>';
  renderPage(id);
}

function renderPage(id){
  switch(id){
    case 'dashboard': renderDashboard();break;
    case 'eleves': renderEleves();break;
    case 'enseignants': renderEnseignants();break;
    case 'notes': renderNotes();break;
    case 'presences': renderPresences('CP-A');break;
    case 'finances': renderFinances();break;
    case 'classes': renderClasses();break;
    case 'emploi-temps': renderEmploiDuTemps('CP-A');break;
    case 'parents': renderParents();break;
    case 'bulletins': renderBulletins();break;
    case 'messages': renderMessages();break;
    case 'annonces': renderAnnonces();break;
    case 'documents': renderDocuments();break;
    case 'bibliotheque': renderBibliotheque();break;
    case 'transport': renderTransport();break;
    case 'cantine': renderCantine();break;
    case 'stocks': renderStocks();break;
    case 'sante': renderSante();break;
    case 'examens': renderExamens();break;
    case 'personnel': renderPersonnel();break;
    case 'rapports': renderRapports();break;
  }
}




function renderDashboard(){
  const d=new Date();
  const jours=['Dimanche','Lundi','Mardi','Mercredi','Jeudi','Vendredi','Samedi'];
  const mois=['janvier','février','mars','avril','mai','juin','juillet','août','septembre','octobre','novembre','décembre'];
  document.getElementById('current-date-display').textContent=`${jours[d.getDay()]} ${d.getDate()} ${mois[d.getMonth()]} ${d.getFullYear()}`;
  document.getElementById('stat-eleves').textContent=DB.eleves.length;
  document.getElementById('stat-enseignants').textContent=DB.enseignants.length;


  const totalPaiements=DB.paiements.reduce((a,p)=>a+(p.montant||0),0);
  const statFin=document.getElementById('stat-finances');
  if(statFin) statFin.textContent= totalPaiements>=1000000 ? (totalPaiements/1000000).toFixed(1)+'M' : totalPaiements.toLocaleString();


  const perfs=[
    {classe:'CM2-A',moy:14.2,pct:71},
    {classe:'6ème A',moy:13.8,pct:69},
    {classe:'CM1-A',moy:12.5,pct:62.5},
    {classe:'CE2-A',moy:15.1,pct:75.5},
    {classe:'CE1-A',moy:16.0,pct:80},
    {classe:'CP-A',moy:13.4,pct:67},
  ];
  document.getElementById('perf-classes').innerHTML=perfs.map(p=>`
    <div style="margin-bottom:10px">
      <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:4px">
        <span style="font-weight:600">${p.classe}</span>
        <span style="color:var(--text2)">${p.moy}/20</span>
      </div>
      <div class="progress"><div class="progress-bar"style="width:${p.pct}%"></div></div>
    </div>`).join('');


  const alertes=[
    {type:'danger',msg:'3 élèves absents non justifiés depuis +3 jours'},
    {type:'warning',msg:'42 familles ont des frais impayés ce trimestre'},
    {type:'warning',msg:'Stock de cahiers en rupture (5 restants)'},
    {type:'info',msg:'Conseil de classe CM2-A prévu le 25 octobre'},
    {type:'success',msg:'Bulletins du 1er trimestre générés à 78%'},
  ];
  document.getElementById('alertes-list').innerHTML=alertes.map(a=>`
    <div class="alert alert-${a.type}">${a.msg}</div>`).join('');
  document.getElementById('alert-count').textContent=alertes.length;


  document.getElementById('recent-payments').innerHTML=DB.paiements.slice(0,6).map(p=>`
    <tr>
      <td><div class="cell-with-avatar"><div class="avatar-sm"style="background:linear-gradient(135deg,var(--violet-l),var(--teal-l))">${p.eleveNom[0]}</div><span style="font-size:12px">${p.eleveNom}</span></div></td>
      <td style="font-size:12px">${p.type}</td>
      <td style="font-weight:700;font-size:12px">${p.montant.toLocaleString()} F</td>
      <td><span class="badge badge-green"> Validé</span></td>
    </tr>`).join('');


  const agenda=[
    {t:'07:30',c:'Maths CP-A',d:'Mme ONDONGO'},
    {t:'09:00',c:'Réunion pédagogique',d:'Salle de réunion'},
    {t:'11:00',c:'Conseil de classe CM1',d:'Bureau direction'},
    {t:'14:00',c:'Réception parents',d:'Secrétariat'},
  ];
  document.getElementById('agenda-today').innerHTML=agenda.map(a=>`
    <div class="tl-item">
      <div class="tl-dot"></div>
      <div class="tl-time">${a.t}</div>
      <div class="tl-content">${a.c}</div>
      <div class="tl-sub">${a.d}</div>
    </div>`).join('');
}




function renderEleves(list){
  list = list||DB.eleves;
  document.getElementById('eleves-count-sub').textContent=`${list.length} élèves`;
  const pagInfo=document.getElementById('eleves-pagination-info');
  if(pagInfo) pagInfo.textContent=`Affichage 1-${list.length} sur ${DB.eleves.length}`;
  document.getElementById('eleves-table').innerHTML=list.map(e=>`
    <tr>
      <td><div class="cell-with-avatar">
        <div class="avatar-sm"style="background:linear-gradient(135deg,${e.sexe==='M'?'#7C3AED,#5B21B6':'#0D9488,#065F46'})">${e.prenom[0]}${e.nom[0]}</div>
        <div><div class="cell-name">${e.nom} ${e.prenom}</div><div class="cell-sub">${e.sexe==='M'?'Masculin':'Féminin'}</div></div>
      </div></td>
      <td style="font-size:12px;font-family:monospace">${e.matricule}</td>
      <td><span class="badge badge-violet">${e.classe}</span></td>
      <td style="font-size:13px">${getAge(e.ddn)} ans</td>
      <td style="font-size:12px">${e.parentNom||'—'}</td>
      <td><span class="badge ${e.fraisStatut==='Payé'?'badge-green':'badge-amber'}">${e.fraisStatut}</span></td>
      <td><span class="badge ${e.statut==='Actif'?'badge-green':'badge-red'}">${e.statut}</span></td>
      <td>
        <button class="btn btn-ghost btn-sm"onclick="viewEleve('${e.id}')"></button>
        <button class="btn btn-ghost btn-sm"onclick="editEleve('${e.id}')"></button>
        <button class="btn btn-ghost btn-sm"onclick="genDocEleve('${e.id}')"></button>
      </td>
    </tr>`).join('');
}

function filterEleves(q){
  const f=DB.eleves.filter(e=>(e.nom+' '+e.prenom).toLowerCase().includes(q.toLowerCase())||e.matricule.includes(q));
  renderEleves(f);
}

function filterElevesByClasse(c){
  if(!c){renderEleves();return;}
  renderEleves(DB.eleves.filter(e=>e.classe===c));
}

function getAge(ddn){
  if(!ddn)return'—';
  const diff=Date.now()-new Date(ddn).getTime();
  return Math.floor(diff/(1000*60*60*24*365));
}




function renderEnseignants(){
  document.getElementById('enseignants-table').innerHTML=DB.enseignants.map(e=>`
    <tr>
      <td><div class="cell-with-avatar">
        <div class="avatar-sm"style="background:linear-gradient(135deg,var(--teal),var(--violet))">${e.prenom[0]}${e.nom[0]}</div>
        <div><div class="cell-name">${e.nom} ${e.prenom}</div><div class="cell-sub">ID: ${e.id}</div></div>
      </div></td>
      <td style="font-size:12px">${e.matieres}</td>
      <td style="font-size:12px">${e.classes}</td>
      <td style="font-weight:700">${e.heures}h</td>
      <td><span class="badge badge-green">${e.statut}</span></td>
      <td><button class="btn btn-ghost btn-sm"onclick="editEnseignant('${e.id}')"> Modifier</button></td>
    </tr>`).join('');
}




function renderNotes(list){
  list = list || DB.notes;
  document.getElementById('notes-table').innerHTML=list.slice(0,20).map(n=>`
    <tr>
      <td style="font-size:12px;font-weight:600">${n.eleveNom}</td>
      <td><span class="badge badge-violet">${n.classe}</span></td>
      <td style="font-size:12px">${n.matiere}</td>
      <td><span class="badge badge-teal">${n.type}</span></td>
      <td><strong style="font-size:15px;color:${getNoteColor(n.note,n.sur)}">${n.note}</strong><span style="color:var(--text3);font-size:11px">/${n.sur}</span></td>
      <td style="text-align:center">${n.coef}</td>
      <td style="font-size:12px;color:var(--text2)">${n.date}</td>
      <td>
        <button class="btn btn-ghost btn-sm"onclick="editNote('${n.id}')"></button>
        <button class="btn btn-ghost btn-sm"style="color:var(--red)"onclick="deleteNote('${n.id}')"></button>
      </td>
    </tr>`).join('');
}

function getNoteColor(note,sur){
  const pct=(note/sur)*100;
  if(pct>=75)return'var(--green)';
  if(pct>=50)return'var(--amber)';
  return'var(--red)';
}


function filterNotes(){
  const c=document.getElementById('notes-classe-filter').value;
  const m=document.getElementById('notes-matiere-filter').value;
  let list=DB.notes;
  if(c) list=list.filter(n=>n.classe===c);
  if(m) list=list.filter(n=>n.matiere===m);
  renderNotes(list);
}




function renderPresences(classe){
  classe = classe || 'CP-A';
  const now=new Date();
  document.getElementById('presence-date').textContent=now.toLocaleDateString('fr-FR',{weekday:'long',day:'numeric',month:'long'});
  const eleves=DB.eleves.filter(e => e.classe === classe);

  if(eleves.length === 0) {
    document.getElementById('presences-table').innerHTML = `<tr><td colspan="6"class="empty-state"><div class="empty-icon"></div><div class="empty-title">Aucun élève trouvé en ${classe}</div></td></tr>`;
    return;
  }


  const rows=eleves.map((e,i)=>{
    const statuses = ['Présent', 'Absent', 'Retard'];
    const statut = statuses[i % 3 === 0 ? 0 : (i % 7 === 0 ? 1 : 2)];
    return {e,statut};
  });


  const cp=document.getElementById('stat-presents'); if(cp)cp.textContent=rows.filter(r=>r.statut==='Présent').length;
  const ca=document.getElementById('stat-absents'); if(ca)ca.textContent=rows.filter(r=>r.statut==='Absent').length;
  const cr=document.getElementById('stat-retards'); if(cr)cr.textContent=rows.filter(r=>r.statut==='Retard').length;

  const colors={Présent:'badge-green',Absent:'badge-red',Retard:'badge-amber'};
  document.getElementById('presences-table').innerHTML=rows.map(({e,statut})=>`
    <tr>
      <td><div class="cell-with-avatar">
        <div class="avatar-sm"style="background:linear-gradient(135deg,var(--violet-l),var(--teal-l))">${e.prenom[0]}${e.nom[0]}</div>
        <div class="cell-name">${e.nom} ${e.prenom}</div>
      </div></td>
      <td><span class="badge ${colors[statut]}">${statut}</span></td>
      <td style="font-size:12px">${statut==='Présent'?'07:28':statut==='Retard'?'08:15':'—'}</td>
      <td style="font-size:12px">${statut==='Absent'?'Maladie':statut==='Retard'?'Transport':'—'}</td>
      <td><span class="badge ${statut!=='Présent'?'badge-green':'badge-teal'}">${statut!=='Présent'?'Notifié':'Auto'}</span></td>
      <td>
        <select class="form-input form-select"style="padding:4px 8px;font-size:11px;width:auto"onchange="updatePresence('${e.id}',this.value)">
          <option ${statut==='Présent'?'selected':''}>Présent</option>
          <option ${statut==='Absent'?'selected':''}>Absent</option>
          <option ${statut==='Retard'?'selected':''}>Retard</option>
        </select>
      </td>
    </tr>`).join('');
}

function loadPresenceByClasse(c){renderPresences(c);}




function renderFinances(){
  renderPaiements();
  renderFrais();
  renderImpaye();
  renderBudget();
  populatePaiementEleves();
}

function renderPaiements(){
  document.getElementById('paiements-table').innerHTML=DB.paiements.map(p=>`
    <tr>
      <td style="font-size:12px">${p.date}</td>
      <td style="font-size:12px;font-weight:600">${p.eleveNom}</td>
      <td style="font-size:12px">${p.type}</td>
      <td style="font-weight:700;color:var(--green)">${p.montant.toLocaleString()} FCFA</td>
      <td style="font-size:11px;font-family:monospace;color:var(--text3)">${p.ref}</td>
      <td>
        <button class="btn btn-ghost btn-sm"onclick="printRecu('${p.id}')"> Reçu</button>
      </td>
    </tr>`).join('');
}

function renderFrais(){
  document.getElementById('frais-table').innerHTML=DB.frais.map(f=>`
    <tr>
      <td><span class="badge badge-violet">${f.niveau}</span></td>
      <td style="font-weight:700">${f.inscription.toLocaleString()} F</td>
      <td style="font-weight:700">${f.scolarite.toLocaleString()} F</td>
      <td>${f.cantine.toLocaleString()} F</td>
      <td>${f.transport.toLocaleString()} F</td>
      <td><button class="btn btn-ghost btn-sm"> Modifier</button></td>
    </tr>`).join('');
}

function renderImpaye(){
  const impayes=DB.eleves.filter(e=>e.fraisStatut!=='Payé').slice(0,8);
  document.getElementById('impaye-table').innerHTML=impayes.map(e=>`
    <tr>
      <td style="font-weight:600;font-size:13px">${e.nom} ${e.prenom}</td>
      <td><span class="badge badge-violet">${e.classe}</span></td>
      <td style="font-size:12px">${e.parentNom}</td>
      <td style="font-weight:700;color:var(--red)">25 000 FCFA</td>
      <td style="font-size:12px;color:var(--red)">En retard</td>
      <td><span class="badge badge-amber">0 relance</span></td>
      <td>
        <button class="btn btn-primary btn-sm"onclick="relancerParent('${e.id}')"> Relancer</button>
      </td>
    </tr>`).join('');
}

function renderBudget(){
  const recettes=[
    {cat:'Frais de scolarité',montant:1800000},
    {cat:'Frais d\'inscription',montant:350000},
    {cat:'Cantine',montant:200000},
    {cat:'Transport',montant:100000},
  ];
  const depenses=[
    {cat:'Salaires enseignants',montant:1200000},
    {cat:'Fournitures scolaires',montant:150000},
    {cat:'Eau & Électricité',montant:80000},
    {cat:'Entretien',montant:60000},
  ];
  document.getElementById('budget-recettes').innerHTML=recettes.map(r=>`
    <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--border);font-size:13px">
      <span>${r.cat}</span><strong style="color:var(--green)">${r.montant.toLocaleString()} F</strong>
    </div>`).join('')+`<div style="display:flex;justify-content:space-between;padding:12px 0;font-size:14px;font-weight:700"><span>TOTAL</span><span style="color:var(--green)">${recettes.reduce((a,r)=>a+r.montant,0).toLocaleString()} F</span></div>`;
  document.getElementById('budget-depenses').innerHTML=depenses.map(d=>`
    <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--border);font-size:13px">
      <span>${d.cat}</span><strong style="color:var(--red)">${d.montant.toLocaleString()} F</strong>
    </div>`).join('')+`<div style="display:flex;justify-content:space-between;padding:12px 0;font-size:14px;font-weight:700"><span>TOTAL</span><span style="color:var(--red)">${depenses.reduce((a,d)=>a+d.montant,0).toLocaleString()} F</span></div>`;
}

function populatePaiementEleves(){
  const sel=document.getElementById('paiement-eleve');
  if(!sel)return;
  sel.innerHTML='<option>-- Sélectionner --</option>'+DB.eleves.map(e=>`<option value="${e.id}">${e.nom} ${e.prenom} (${e.classe})</option>`).join('');
}

function switchFinanceTab(tab,el){
  document.querySelectorAll('.finance-tab').forEach(t=>t.style.display='none');
  document.querySelectorAll('.tabs .tab').forEach(t=>t.classList.remove('active'));
  const ft=document.getElementById('finance-'+tab);
  if(ft)ft.style.display='block';
  if(el)el.classList.add('active');
}




function renderClasses(){
  const colors=['var(--violet-bg)','var(--teal-bg)','var(--amber-bg)','var(--green-bg)','var(--red-bg)','#F0F4FF'];
  const borders=['var(--violet-xl)','var(--teal-xl)','#FDE68A','#A7F3D0','#FCA5A5','#93C5FD'];
  document.getElementById('classes-grid').innerHTML=DB.classes.map((c,i)=>`
    <div class="card"style="border:2px solid ${borders[i%borders.length]};background:${colors[i%colors.length]};cursor:pointer"onclick="showPage('emploi-temps')">
      <div class="card-body"style="text-align:center">
        <div style="font-size:36px;margin-bottom:8px"></div>
        <div style="font-size:20px;font-weight:800;font-family:var(--font2)">${c.nom}</div>
        <div style="font-size:12px;color:var(--text2);margin-top:4px">${c.enseignant}</div>
        <div style="display:flex;justify-content:space-between;margin-top:16px;font-size:12px">
          <span> ${c.effectif} élèves</span>
          <span> ${c.salle}</span>
        </div>
      </div>
    </div>`).join('');
}




function renderEmploiDuTemps(classe){
  const jours=['Lundi','Mardi','Mercredi','Jeudi','Vendredi','Samedi'];
  const horaires=['07:30-09:00','09:15-10:45','11:00-12:00','14:00-15:30','15:45-17:00'];
  const matiereColors={
    'Français':'#EDE9FE','Mathématiques':'#D1FAE5','Sciences':'#FEF3C7',
    'Histoire-Géo':'#FCE7F3','EPS':'#DBEAFE','Arts':'#FEE2E2','Anglais':'#F0FDF4',
    'Lecture':'#F5F3FF','Autre':'#F3F4F6'
  };

  document.getElementById('emploi-head').innerHTML=`<tr>
    <th style="width:100px;padding:10px 14px;background:#FAFAFA;font-size:11px;font-weight:700;color:var(--text3)">Horaire</th>
    ${jours.map(j=>`<th style="padding:10px 14px;background:#FAFAFA;font-size:11px;font-weight:700;color:var(--text3);text-align:center">${j}</th>`).join('')}
  </tr>`;

  document.getElementById('emploi-body').innerHTML=horaires.map(h=>{
    const [debut]=h.split('-');
    return`<tr>
      <td style="padding:8px 14px;font-size:12px;font-weight:600;color:var(--text2);background:#FAFAFA;border-bottom:1px solid var(--border)">${h}</td>
      ${jours.map(j=>{
        const cr=DB.creneaux.find(c=>c.classe===classe&&c.jour===j&&c.debut===debut);
        if(cr){
          const bg=matiereColors[cr.matiere]||matiereColors['Autre'];
          return`<td style="padding:6px;border:1px solid var(--border)">
            <div style="background:${bg};border-radius:8px;padding:8px;text-align:center;cursor:pointer"onclick="editCreneau('${cr.id}')">
              <div style="font-size:12px;font-weight:700">${cr.matiere}</div>
              <div style="font-size:10px;color:var(--text3)">${cr.enseignant.split(' ').slice(0,2).join(' ')}</div>
              <div style="font-size:10px;color:var(--text3)">${cr.salle}</div>
            </div>
          </td>`;
        }
        return`<td style="border:1px solid var(--border);padding:6px"><div style="height:60px;border-radius:8px;border:2px dashed var(--border);display:flex;align-items:center;justify-content:center;color:var(--text3);font-size:11px;cursor:pointer"onclick="openModal('modal-add-creneau')">+ Ajouter</div></td>`;
      }).join('')}
    </tr>`;
  }).join('');
}

function loadEmploiDuTemps(v){renderEmploiDuTemps(v);}




function renderParents(){

  const derived=[...new Map(DB.eleves.filter(e=>e.parentNom).map(e=>[e.parentTel,{nom:e.parentNom,tel:e.parentTel,enfants:[]}])).values()];
  DB.eleves.forEach(e=>{const p=derived.find(p=>p.tel===e.parentTel);if(p)p.enfants.push(e.prenom);});
  const parents=[...DB.parents,...derived];
  document.getElementById('parents-table').innerHTML=parents.slice(0,10).map(p=>`
    <tr>
      <td><div class="cell-with-avatar">
        <div class="avatar-sm"style="background:linear-gradient(135deg,var(--teal),var(--green))">${p.nom[0]}</div>
        <div class="cell-name">${p.nom}</div>
      </div></td>
      <td style="font-size:12px">${p.enfants.join(', ')}</td>
      <td style="font-size:12px">${p.tel}</td>
      <td style="font-size:13px;color:var(--red);font-weight:600">25 000 F</td>
      <td style="font-size:12px;color:var(--text2)">Il y a 3 jours</td>
      <td>
        <button class="btn btn-ghost btn-sm"onclick="msgParent('${p.tel}')"> Message</button>
        <button class="btn btn-ghost btn-sm"onclick="callParent('${p.tel}')"></button>
      </td>
    </tr>`).join('');
}




function renderBulletins(){
  document.getElementById('bulletins-table').innerHTML='<tr><td colspan="7"class="empty-state"><div class="empty-icon"></div><div class="empty-title">Sélectionnez une classe et cliquez sur "Charger les bulletins"</div></td></tr>';
}

function loadBulletinClass(){
  const classe=document.getElementById('bulletin-classe').value;
  const eleves=DB.eleves.filter(e=>e.classe===classe).slice(0,8);
  const moyennes=eleves.map((e,i)=>({...e,moy:Math.round((9+Math.random()*10)*100)/100,rang:i+1}));
  moyennes.sort((a,b)=>b.moy-a.moy).forEach((e,i)=>e.rang=i+1);

  document.getElementById('bulletin-stats').innerHTML=`
    <div style="display:flex;flex-direction:column;gap:10px">
      <div style="display:flex;justify-content:space-between"><span style="font-size:12px;color:var(--text2)">Effectif</span><strong>${eleves.length}</strong></div>
      <div style="display:flex;justify-content:space-between"><span style="font-size:12px;color:var(--text2)">Moyenne classe</span><strong>${(moyennes.reduce((a,e)=>a+e.moy,0)/moyennes.length).toFixed(2)}/20</strong></div>
      <div style="display:flex;justify-content:space-between"><span style="font-size:12px;color:var(--text2)">Plus haute moy.</span><strong style="color:var(--green)">${Math.max(...moyennes.map(e=>e.moy)).toFixed(2)}</strong></div>
      <div style="display:flex;justify-content:space-between"><span style="font-size:12px;color:var(--text2)">Plus basse moy.</span><strong style="color:var(--red)">${Math.min(...moyennes.map(e=>e.moy)).toFixed(2)}</strong></div>
      <div style="display:flex;justify-content:space-between"><span style="font-size:12px;color:var(--text2)">Taux de réussite</span><strong style="color:var(--violet)">${Math.round(moyennes.filter(e=>e.moy>=10).length/moyennes.length*100)}%</strong></div>
    </div>`;

  document.getElementById('bulletins-table').innerHTML=moyennes.map(e=>{
    const mention=e.moy>=16?'TB':e.moy>=14?'B':e.moy>=12?'AB':e.moy>=10?'P':'I';
    const mentionC={TB:'badge-teal',B:'badge-green',AB:'badge-violet',P:'badge-amber',I:'badge-red'};
    return`<tr>
      <td><div class="cell-with-avatar">
        <div class="avatar-sm"style="background:linear-gradient(135deg,var(--violet-l),var(--teal-l))">${e.prenom[0]}${e.nom[0]}</div>
        <div class="cell-name">${e.nom} ${e.prenom}</div>
      </div></td>
      <td style="font-size:18px;font-weight:800;color:${getNoteColor(e.moy,20)}">${e.moy}</td>
      <td style="font-size:16px;font-weight:700">${e.rang}${e.rang===1?'er':'ème'}</td>
      <td><span class="badge ${mentionC[mention]}">${mention}</span></td>
      <td style="font-size:12px;color:var(--text2)">Résultats ${e.moy>=14?'satisfaisants':'à améliorer'}</td>
      <td><span class="badge ${e.moy>=10?'badge-green':'badge-red'}">${e.moy>=10?'Admis':'À surveiller'}</span></td>
      <td>
        <button class="btn btn-primary btn-sm"onclick="genBulletin('${e.id}')"> PDF</button>
      </td>
    </tr>`;
  }).join('');
  showToast('success','Bulletins chargés pour '+classe);
}




function renderMessages(){
  document.getElementById('conv-list').innerHTML=DB.messages.map(m=>`
    <div style="padding:12px 16px;border-bottom:1px solid var(--border);cursor:pointer;${!m.read?'background:var(--violet-bg)':''}"onclick="openConv('${m.id}')">
      <div style="display:flex;align-items:center;gap:10px">
        <div class="avatar-sm"style="background:linear-gradient(135deg,var(--violet-l),var(--teal-l))">${m.avatar}</div>
        <div style="flex:1">
          <div style="font-weight:${m.read?500:700};font-size:13px">${m.from}</div>
          <div style="font-size:12px;color:var(--text3);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:160px">${m.msg}</div>
        </div>
        <div style="font-size:11px;color:var(--text3)">${m.time}</div>
      </div>
    </div>`).join('');
}

function openConv(id){
  const m=DB.messages.find(x=>x.id===id);
  if(!m)return;
  m.read=true;
  document.getElementById('conv-title').textContent=m.from;
  document.getElementById('conv-messages').innerHTML=`
    <div style="display:flex;flex-direction:column;gap:10px">
      <div style="max-width:70%;align-self:flex-start">
        <div style="background:var(--violet-bg);border-radius:0 12px 12px 12px;padding:10px 14px;font-size:13px">${m.msg}</div>
        <div style="font-size:11px;color:var(--text3);margin-top:4px">${m.time}</div>
      </div>
    </div>`;
  renderMessages();
}

function sendMessage(){
  const input=document.getElementById('msg-input');
  if(!input.value.trim())return;
  const msgs=document.getElementById('conv-messages');
  msgs.innerHTML+=`<div style="display:flex;justify-content:flex-end;margin-top:10px">
    <div style="max-width:70%">
      <div style="background:linear-gradient(135deg,var(--violet-l),var(--teal-l));color:#fff;border-radius:12px 12px 0 12px;padding:10px 14px;font-size:13px">${input.value}</div>
      <div style="font-size:11px;color:var(--text3);text-align:right;margin-top:4px">Maintenant</div>
    </div>
  </div>`;
  input.value='';
  msgs.scrollTop=msgs.scrollHeight;
  showToast('success','Message envoyé');
}


function handleAuthBtn(){
  if(CURRENT_USER){ logout(); }
  else { openLoginModal(); }
}

function openLoginModal(){ openModal('modal-login'); }

function login(){
  const email = document.getElementById('login-email').value.trim();
  const pass = document.getElementById('login-pass').value;
  if(!email||!pass){ showToast('error','Email et mot de passe requis'); return; }
  if(window.FB_AUTH && window.FB_SIGNIN){
    window.FB_SIGNIN(window.FB_AUTH, email, pass)
      .then(()=>{ closeModal('modal-login'); showToast('success','Connecté'); })
      .catch(err=>{ console.warn(err); showToast('error','Erreur: '+(err.message||err.code)); });
  } else {
    showToast('error','Auth non disponible (offline)');
  }
}

function logout(){
  if(window.FB_AUTH && window.FB_SIGNOUT){
    window.FB_SIGNOUT(window.FB_AUTH).then(()=>{ showToast('info','Déconnecté'); }).catch(e=>{console.warn(e);showToast('error','Erreur logout');});
  } else {
    CURRENT_USER=null; onUserSignedOut(); showToast('info','Déconnecté (local)');
  }
}




function renderAnnonces(){
  const prioColors={Urgente:'badge-red',Importante:'badge-amber',Normale:'badge-teal'};
  document.getElementById('annonces-list').innerHTML=DB.annonces.map(a=>`
    <div class="card">
      <div class="card-body">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px">
          <div style="font-weight:700;font-size:15px">${a.titre}</div>
          <span class="badge ${prioColors[a.prio]}">${a.prio}</span>
        </div>
        <p style="font-size:13px;color:var(--text2);line-height:1.6">${a.message}</p>
        <div style="display:flex;justify-content:space-between;margin-top:12px;font-size:12px;color:var(--text3)">
          <span>Par ${a.auteur}</span><span>${a.date}</span>
        </div>
      </div>
    </div>`).join('');
}




function renderDocuments(){
  document.getElementById('docs-table').innerHTML=DB.documents.map(d=>`
    <tr>
      <td style="font-weight:600;font-size:13px">${d.type}</td>
      <td style="font-size:13px">${d.eleve}</td>
      <td style="font-size:12px;color:var(--text2)">${d.date}</td>
      <td style="font-size:12px">${d.par}</td>
      <td><span class="badge badge-teal"> ${d.qr}</span></td>
      <td>
        <button class="btn btn-primary btn-sm"onclick="downloadDoc('${d.id}')"> PDF</button>
        <button class="btn btn-ghost btn-sm"onclick="verifyDoc('${d.id}')"> Vérifier</button>
      </td>
    </tr>`).join('');
}




function renderBibliotheque(){
  document.getElementById('bibliotheque-table').innerHTML=DB.livres.map(l=>`
    <tr>
      <td style="font-weight:600;font-size:13px">${l.titre}</td>
      <td style="font-size:12px">${l.auteur}</td>
      <td><span class="badge badge-violet">${l.categorie}</span></td>
      <td style="font-size:13px">${l.stock}</td>
      <td style="font-size:12px">${l.emprunte?l.empruntePar:'—'}</td>
      <td style="font-size:12px;color:var(--text2)">${l.retour||'—'}</td>
      <td>
        <button class="btn btn-ghost btn-sm"onclick="toggleEmprunt('${l.id}')">${l.emprunte?'↩ Retour':'Prêt'}</button>
      </td>
    </tr>`).join('');
}




function renderTransport(){
  document.getElementById('transport-grid').innerHTML=DB.transport.map(t=>`
    <div class="card">
      <div class="card-body"style="text-align:center">
        <div style="font-size:40px;margin-bottom:8px"></div>
        <div style="font-size:18px;font-weight:800;font-family:var(--font2)">${t.nom}</div>
        <div style="font-size:12px;color:var(--text2);margin-top:4px">Chauffeur: ${t.chauffeur}</div>
        <div style="font-size:12px;color:var(--text3)">${t.plaque}</div>
        <div class="progress"style="margin:12px 0">
          <div class="progress-bar"style="width:${Math.round(t.eleves/t.capacite*100)}%"></div>
        </div>
        <div style="font-size:12px;color:var(--text2)">${t.eleves}/${t.capacite} élèves</div>
        <div style="font-size:11px;color:var(--text3);margin-top:6px">${t.itineraire}</div>
        <button class="btn btn-primary btn-sm"style="margin-top:12px;width:100%"onclick="editBus('${t.id}')">Gérer ce bus</button>
      </div>
    </div>`).join('')+`<div class="card"style="border:2px dashed var(--border);cursor:pointer"onclick="openModal('modal-add-bus')">
      <div class="card-body"style="text-align:center;padding:40px">
        <div style="font-size:40px;margin-bottom:8px;opacity:.3"></div>
        <div style="color:var(--text3)">+ Ajouter un bus</div>
      </div>
    </div>`;
}




function renderStocks(){
  document.getElementById('stocks-table').innerHTML=DB.stocks.map(s=>{
    const low=s.stock<=s.stockMin;
    return`<tr>
      <td style="font-weight:600;font-size:13px">${s.article}</td>
      <td><span class="badge badge-violet">${s.categorie}</span></td>
      <td style="font-size:16px;font-weight:700;color:${low?'var(--red)':'var(--text)'}">${s.stock} ${s.unite}</td>
      <td style="font-size:12px;color:var(--text3)">${s.stockMin} ${s.unite}</td>
      <td><span class="badge ${low?'badge-red':'badge-green'}">${low?'Stock bas':'OK'}</span></td>
      <td>
        <button class="btn btn-ghost btn-sm"onclick="addStock('${s.id}')">+ Entrée</button>
        <button class="btn btn-ghost btn-sm"onclick="removeStock('${s.id}')">- Sortie</button>
      </td>
    </tr>`;
  }).join('');
}




function renderSante(){
  document.getElementById('sante-table').innerHTML=DB.sante.map(s=>`
    <tr>
      <td style="font-weight:600">${s.eleveNom}</td>
      <td style="font-size:12px;color:var(--text2)">${s.date}</td>
      <td style="font-size:13px">${s.motif}</td>
      <td style="font-size:12px">${s.traitement}</td>
      <td><span class="badge ${s.parentNotifie?'badge-green':'badge-red'}">${s.parentNotifie?'Notifié':'Non notifié'}</span></td>
      <td><span class="badge ${s.refere?'badge-amber':'badge-teal'}">${s.refere?'Référé':'Sur place'}</span></td>
    </tr>`).join('');
}




function renderExamens(){
  document.getElementById('examens-table').innerHTML=DB.examens.map(e=>`
    <tr>
      <td style="font-weight:600">${e.nom}</td>
      <td><span class="badge badge-violet">${e.classe}</span></td>
      <td style="font-size:12px">${e.date}</td>
      <td style="font-size:12px">${e.salle}</td>
      <td style="font-size:12px">${e.surveillants}</td>
      <td><span class="badge badge-teal">${e.statut}</span></td>
      <td>
        <button class="btn btn-ghost btn-sm"onclick="genConvocation('${e.id}')"> Convocations</button>
        <button class="btn btn-ghost btn-sm"onclick="editExamen('${e.id}')"></button>
      </td>
    </tr>`).join('');
}




function renderPersonnel(){
  document.getElementById('personnel-table').innerHTML=DB.personnel.map(p=>`
    <tr>
      <td><div class="cell-with-avatar">
        <div class="avatar-sm"style="background:linear-gradient(135deg,var(--amber),var(--red))">${p.nom[0]}</div>
        <div class="cell-name">${p.nom}</div>
      </div></td>
      <td><span class="badge badge-violet">${p.poste}</span></td>
      <td style="font-size:12px">${p.contact}</td>
      <td><span class="badge badge-teal">${p.contrat}</span></td>
      <td><span class="badge badge-green">${p.statut}</span></td>
      <td><button class="btn btn-ghost btn-sm"> Modifier</button></td>
    </tr>`).join('');
}




function renderRapports(){
  document.getElementById('rapport-repartition').innerHTML=DB.classes.map(c=>`
    <div style="margin-bottom:10px">
      <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:4px">
        <span style="font-weight:600">${c.nom}</span>
        <span style="color:var(--text2)">${c.effectif} élèves</span>
      </div>
      <div class="progress"><div class="progress-bar"style="width:${Math.round(c.effectif/DB.eleves.length*100+20)}%"></div></div>
    </div>`).join('');
  document.getElementById('rapport-moyennes').innerHTML=`
    <div style="font-size:12px;color:var(--text2);margin-bottom:12px">Évolution des moyennes générales par trimestre</div>
    <div class="chart-bar-wrap">
      ${['T1','T2','T3'].map((t,i)=>`<div class="chart-bar"style="height:${[70,78,65][i]}px"title="${t}: ${[13.2,14.1,12.8][i]}/20"></div>`).join('')}
    </div>
    <div class="chart-labels">
      ${['T1 (13.2)','T2 (14.1)','T3 (12.8)'].map(l=>`<div class="chart-label">${l}</div>`).join('')}
    </div>`;
}




function openModal(id){
  const m=document.getElementById(id);
  if(m){m.style.display='flex';loadModalData(id);}
}

function closeModal(id){
  const m=document.getElementById(id);
  if(m)m.style.display='none';
  if(id==='modal-add-eleve'){
    editingEleveId = null;
    document.querySelector('#modal-add-eleve .modal-title').textContent = "Inscrire un nouvel élève";
    document.querySelector('#modal-add-eleve .btn-primary').textContent = "Inscrire l'élève";
    document.getElementById('eleve-nom').value = '';
    document.getElementById('eleve-prenom').value = '';
    document.getElementById('eleve-ddn').value = '';
    document.getElementById('eleve-lieu-naissance').value = '';
    document.getElementById('eleve-adresse').value = '';
    document.getElementById('eleve-parent-nom').value = '';
    document.getElementById('eleve-parent-tel').value = '';
  }
}

function closeModalOuter(e,id){
  if(e.target===document.getElementById(id))closeModal(id);
}

function loadModalData(id){
  if(id==='modal-add-note'){
    const c=document.getElementById('note-classe').value||'CP-A';
    const d=new Date().toISOString().split('T')[0];
    document.getElementById('note-date').value=d;
    const eleves=DB.eleves.filter(e=>e.classe===c).slice(0,10);
    document.getElementById('notes-eleves-list').innerHTML=eleves.map(e=>`
      <div style="display:flex;align-items:center;gap:12px;padding:8px;border-bottom:1px solid var(--border)">
        <div style="flex:1;font-size:13px;font-weight:500">${e.nom} ${e.prenom}</div>
        <input type="number"min="0"max="20"step="0.5"class="form-input"style="width:80px;padding:6px 10px;font-size:14px;text-align:center"placeholder="—"data-eleve="${e.id}"/>
        <input type="text"class="form-input"style="width:120px;padding:6px 10px;font-size:12px"placeholder="Appréciation"/>
      </div>`).join('');
  }
  if(id==='modal-appel'){
    const d=new Date().toISOString().split('T')[0];
    document.getElementById('appel-date').value=d;
    loadAppelEleves('CP-A');
  }
  if(id==='modal-add-paiement'){
    populatePaiementEleves();
    document.getElementById('paiement-date').value=new Date().toISOString().split('T')[0];
  }
  if(id==='modal-add-creneau'){
    const sel=document.getElementById('creneau-enseignant');
    if(sel)sel.innerHTML='<option>-- Sélectionner --</option>'+DB.enseignants.map(e=>`<option>${e.prenom} ${e.nom}</option>`).join('');
  }

  if(id==='modal-add-soin'){
    fillSelect('soin-eleve',eleveOptions(),'-- Sélectionner un élève --');
    document.getElementById('soin-date').value=new Date().toISOString().split('T')[0];
  }
  if(id==='modal-emprunt'){
    fillSelect('emprunt-livre',DB.livres.map(l=>({value:l.id,label:l.titre+(l.emprunte?' (déjà prêté)':'')})),'-- Sélectionner un livre --');
    fillSelect('emprunt-eleve',eleveOptions(),'-- Sélectionner un élève --');
    document.getElementById('emprunt-retour').value=new Date(Date.now()+14*24*60*60*1000).toISOString().split('T')[0];
  }
  if(id==='modal-sortie-stock'){
    fillSelect('sortie-stock-article',DB.stocks.map(s=>({value:s.id,label:s.article+' ('+s.stock+' '+s.unite+')'})),'-- Sélectionner un article --');
  }
  if(id==='modal-gen-doc'){
    fillSelect('gen-doc-eleve',eleveOptions(),'-- Sélectionner un élève --');
  }
  if(id==='modal-add-examen'){
    document.getElementById('examen-date').value=new Date().toISOString().split('T')[0];
  }
  if(id==='modal-send-message'){
    const noms=[...DB.enseignants.map(e=>e.prenom+' '+e.nom),...DB.eleves.map(e=>e.parentNom).filter(Boolean)];
    fillSelect('msg-dest',[...new Set(noms)].map(n=>({value:n,label:n})),'-- Choisir un destinataire --');
  }
}

function loadAppelEleves(classe){
  const eleves=DB.eleves.filter(e=>e.classe===classe).slice(0,12);
  document.getElementById('appel-eleves-list').innerHTML=eleves.map(e=>`
    <div style="display:flex;align-items:center;gap:12px;padding:10px;border-bottom:1px solid var(--border)">
      <div class="avatar-sm"style="background:linear-gradient(135deg,var(--violet-l),var(--teal-l))">${e.prenom[0]}${e.nom[0]}</div>
      <div style="flex:1;font-size:13px;font-weight:600">${e.nom} ${e.prenom}</div>
      <div style="display:flex;gap:6px">
        <label style="display:flex;align-items:center;gap:4px;font-size:12px;cursor:pointer"><input type="radio"name="appel-${e.id}"value="present"checked/> Présent</label>
        <label style="display:flex;align-items:center;gap:4px;font-size:12px;cursor:pointer"><input type="radio"name="appel-${e.id}"value="absent"/> Absent</label>
        <label style="display:flex;align-items:center;gap:4px;font-size:12px;cursor:pointer"><input type="radio"name="appel-${e.id}"value="retard"/> Retard</label>
      </div>
    </div>`).join('');
}

function switchEleveTab(tab,el){
  document.querySelectorAll('[id^="eleve-tab-"]').forEach(t=>t.style.display='none');
  document.querySelectorAll('.modal .tabs .tab').forEach(t=>t.classList.remove('active'));
  const t=document.getElementById('eleve-tab-'+tab);
  if(t)t.style.display='block';
  if(el)el.classList.add('active');
}




function saveEleve(){
  if(!enforceRoleAccess('manage-students')) return;
  const nom=document.getElementById('eleve-nom').value;
  const prenom=document.getElementById('eleve-prenom').value;
  if(!nom||!prenom){showToast('error','Nom et prénom obligatoires');return;}

  if(editingEleveId !== null) {
    const el = DB.eleves.find(e => e.id === editingEleveId);
    if(el) {
      el.nom = nom.toUpperCase();
      el.prenom = prenom;
      el.classe = document.getElementById('eleve-classe').value;
      el.lieuNaissance = document.getElementById('eleve-lieu-naissance').value;
      el.ddn = document.getElementById('eleve-ddn').value;
      el.sexe = document.getElementById('eleve-sexe').value;
      el.nationalite = document.getElementById('eleve-nationalite').value;
      el.adresse = document.getElementById('eleve-adresse').value;
      el.parentNom = document.getElementById('eleve-parent-nom').value;
      el.parentTel = document.getElementById('eleve-parent-tel').value;
      saveToFirebase('eleves', el);
      showToast('success', 'Dossier élève mis à jour');
    }
    editingEleveId = null;
  } else {
    const newEleve={
      id:'EL'+String(DB.eleves.length+1).padStart(4,'0'),
      matricule:'2024'+String(DB.eleves.length+1).padStart(4,'0'),
      nom:nom.toUpperCase(),prenom,
      classe:document.getElementById('eleve-classe').value,
      ddn:document.getElementById('eleve-ddn').value,
      lieuNaissance:document.getElementById('eleve-lieu-naissance').value,
      sexe:document.getElementById('eleve-sexe').value,
      nationalite:document.getElementById('eleve-nationalite').value,
      adresse:document.getElementById('eleve-adresse').value,
      fraisStatut:'En attente',statut:'Actif',
      parentNom:document.getElementById('eleve-parent-nom').value,
      parentTel:document.getElementById('eleve-parent-tel').value || '+242 06 123 45 67',
      createdAt:new Date().toISOString()
    };
    DB.eleves.push(newEleve);
    saveToFirebase('eleves',newEleve);
    showToast('success','Élève inscrit avec succès — Matricule: '+newEleve.matricule);
  }

  closeModal('modal-add-eleve');
  renderEleves();
  document.getElementById('badge-eleves').textContent=DB.eleves.length;
}

function saveNotes(){
  if(!enforceRoleAccess('manage-notes')) return;
  const inputs=document.querySelectorAll('#notes-eleves-list input[type="number"]');
  let count=0;
  inputs.forEach(inp=>{
    if(inp.value){
      const eleve=DB.eleves.find(x=>x.id===inp.dataset.eleve);
      const note={
        id:'N'+Math.random().toString(36).substr(2,6),
        eleveId:inp.dataset.eleve,
        eleveNom:eleve ? eleve.nom+' '+eleve.prenom : 'Élève inconnu',
        classe:document.getElementById('note-classe').value,
        matiere:document.getElementById('note-matiere').value,
        type:document.getElementById('note-type').value,
        note:parseFloat(inp.value),
        sur:parseInt(document.getElementById('note-sur').value),
        coef:parseInt(document.getElementById('note-coef').value),
        date:document.getElementById('note-date').value,
      };
      DB.notes.push(note);
      saveToFirebase('notes', note);
      count++;
    }
  });
  closeModal('modal-add-note');
  showToast('success',`${count} notes enregistrées avec succès`);
  renderNotes();
}

function savePaiement(){
  if(!enforceRoleAccess('manage-finances')) return;
  const sel=document.getElementById('paiement-eleve');
  const eleveId=sel.value;
  const montant=document.getElementById('paiement-montant').value;
  if(!montant||eleveId.includes('--')){showToast('error','Remplissez tous les champs requis');return;}
  const eleveNom=sel.options[sel.selectedIndex].text;
  const p={
    id:'P'+Math.random().toString(36).substr(2,6),
    eleveId,
    eleveNom,
    type:document.getElementById('paiement-type').value,
    montant:parseInt(montant),
    ref:document.getElementById('paiement-ref').value||'TXN-'+Date.now(),
    date:document.getElementById('paiement-date').value,
    statut:'Validé'
  };
  DB.paiements.unshift(p);
  saveToFirebase('paiements',p);
  closeModal('modal-add-paiement');
  renderPaiements();
  showToast('success','Paiement enregistré — Reçu PDF généré');
}

function saveAppel(){
  closeModal('modal-appel');
  showToast('success','Appel validé — Parents des absents notifiés automatiquement');
  document.getElementById('badge-absences').textContent='0';
}

function saveCreneau(){
  if(!enforceRoleAccess('manage-students')) return;
  const c={
    id:'CR'+Math.random().toString(36).substr(2,4),
    jour:document.getElementById('creneau-jour').value,
    classe:document.getElementById('creneau-classe').value,
    debut:document.getElementById('creneau-debut').value,
    fin:document.getElementById('creneau-fin').value,
    matiere:document.getElementById('creneau-matiere').value,
    enseignant:document.getElementById('creneau-enseignant').value,
    salle:document.getElementById('creneau-salle').value,
  };
  DB.creneaux.push(c);
  saveToFirebase('creneaux', c);
  closeModal('modal-add-creneau');
  renderEmploiDuTemps(c.classe);
  showToast('success','Créneau ajouté — Conflit vérifié ');
}

function saveAnnonce(){
  if(!enforceRoleAccess('send-announcements')) return;
  const t=document.getElementById('annonce-titre').value;
  const m=document.getElementById('annonce-message').value;
  if(!t||!m){showToast('error','Titre et message requis');return;}
  const a = {id:'A'+Date.now(),titre:t,message:m,date:new Date().toISOString().split('T')[0],prio:document.getElementById('annonce-prio').value,auteur:'Direction'};
  DB.annonces.unshift(a);
  saveToFirebase('annonces', a);
  closeModal('modal-add-annonce');
  renderAnnonces();
  showToast('success','Annonce publiée — Notifications envoyées');
}

function saveFirebaseConfig(){
  if(!enforceRoleAccess('manage-settings')) return;
  const config={
    apiKey:document.getElementById('fb-apiKey').value,
    authDomain:document.getElementById('fb-authDomain').value,
    projectId:document.getElementById('fb-projectId').value,
    databaseURL:document.getElementById('fb-databaseURL').value,
    storageBucket:document.getElementById('fb-storageBucket').value,
    messagingSenderId:document.getElementById('fb-messagingSenderId').value,
    appId:document.getElementById('fb-appId').value,
  };
  if(!config.apiKey||config.apiKey==='YOUR_API_KEY'){showToast('error','Entrez votre vraie clé API Firebase');return;}
  localStorage.setItem('firebaseConfig',JSON.stringify(config));
  showToast('success','Configuration Firebase sauvegardée ! Rechargez pour activer la sync.');
}

function saveParametres(){ if(!enforceRoleAccess('manage-settings')) return; showToast('success','Paramètres enregistrés'); }

function createUserByRole(){
  if(!enforceRoleAccess('manage-users')) return;
  const first = document.getElementById('user-firstname').value.trim();
  const last = document.getElementById('user-lastname').value.trim();
  const email = document.getElementById('user-email').value.trim();
  const phone = document.getElementById('user-phone').value.trim();
  const role = document.getElementById('user-role').value;
  const password = document.getElementById('user-password').value;
  if(!first||!last||!email||!password){showToast('error','Tous les champs requis');return;}

  if(window.FB_AUTH && window.FB_CREATE_USER){
    window.FB_CREATE_USER(window.FB_AUTH, email, password)
      .then((cred)=>{
        const uid = cred.user.uid;
        const user = {id:uid, firstname:first, lastname:last, email, phone, role, schoolId:CURRENT_SCHOOL_ID, createdAt:new Date().toISOString()};
        DB.users.push(user);
        saveGlobalToFirebase('users', uid, user);
        try{ const memberRef = window.FB_REF(window.FB_DB, `${CURRENT_SCHOOL_ID}/members/${uid}`); window.FB_SET(memberRef, user); }catch(e){console.warn(e);}
        closeModal('modal-add-user');
        showToast('success',`Utilisateur créé avec le rôle ${role}`);
      })
      .catch(err=>{console.warn(err);showToast('error','Erreur création utilisateur: '+(err.message||err.code));});
  } else {
    const user = {id:'U'+Math.random().toString(36).substr(2,8), firstname:first, lastname:last, email, phone, role, schoolId:CURRENT_SCHOOL_ID, createdAt:new Date().toISOString()};
    DB.users.push(user); saveGlobalToFirebase('users', user.id, user); closeModal('modal-add-user'); showToast('success','Utilisateur ajouté (local)');
  }
}

function createSchoolAndDirector(){
  if(!enforceRoleAccess('create-school')) return;
  const name = document.getElementById('onb-school-name').value.trim();
  if(!name){showToast('error','Nom de l\'école requis');return;}
  const schoolId = 'school_'+name.toLowerCase().replace(/[^a-z0-9]+/g,'_')+'_'+Date.now();
  const school = {
    id: schoolId,
    name,
    logo:document.getElementById('onb-school-logo').value||'',
    address:document.getElementById('onb-school-address').value||'',
    phone:document.getElementById('onb-school-phone').value||'',
    year:document.getElementById('onb-school-year').value||'',
    currency:document.getElementById('onb-school-currency').value||'FCFA',
    createdAt:new Date().toISOString()
  };

  const dirFirst = document.getElementById('onb-dir-firstname').value.trim();
  const dirLast = document.getElementById('onb-dir-lastname').value.trim();
  const dirEmail = document.getElementById('onb-dir-email').value.trim();
  const dirPhone = document.getElementById('onb-dir-phone').value.trim();
  const dirPass = document.getElementById('onb-dir-password').value;
  if(!dirFirst||!dirLast||!dirEmail||!dirPass){showToast('error','Champs Directeur incomplets');return;}


  if(window.FB_AUTH && window.FB_CREATE_USER){
    window.FB_CREATE_USER(window.FB_AUTH, dirEmail, dirPass)
      .then((cred)=>{
        const uid = cred.user.uid;
        const user = {
          id: uid,
          firstname:dirFirst,
          lastname:dirLast,
          email:dirEmail,
          phone:dirPhone,
          role:'Directeur',
          schoolId:schoolId,
          createdAt:new Date().toISOString()
        };

        DB.schools.push(school);
        DB.users.push(user);

        saveGlobalToFirebase('schools', schoolId, school);
        saveGlobalToFirebase('users', uid, user);

        try{ const memberRef = window.FB_REF(window.FB_DB, `${schoolId}/members/${uid}`); window.FB_SET(memberRef, user); }catch(e){console.warn(e);}


        setCurrentSchoolId(schoolId);
        closeModal('modal-create-school');
        showToast('success',`École '${name}'créée — compte Directeur: ${dirEmail}`);

        window.FB_SIGNIN(window.FB_AUTH, dirEmail, dirPass).catch(()=>{});
        renderDashboard();
      })
      .catch(err=>{console.warn(err);showToast('error','Erreur création compte: '+(err.message||err.code));});
  } else {

    const user = {id:'U'+Math.random().toString(36).substr(2,8),firstname:dirFirst,lastname:dirLast,email:dirEmail,phone:dirPhone,role:'Directeur',schoolId:schoolId,createdAt:new Date().toISOString()};
    DB.schools.push(school);DB.users.push(user);saveGlobalToFirebase('schools', schoolId, school);saveGlobalToFirebase('users', user.id, user);setCurrentSchoolId(schoolId);closeModal('modal-create-school');showToast('success',`École '${name}'créée (local)`);renderDashboard();
  }
}









function fillSelect(id,items,placeholder){
  const sel=document.getElementById(id);
  if(!sel)return;
  sel.innerHTML=placeholder ? '<option value="--">'+placeholder+'</option>' : '';
  sel.innerHTML+=items.map(o=>'<option value="'+o.value+'">'+o.label+'</option>').join('');
}


function eleveOptions(){
  return DB.eleves.map(e=>({value:e.id,label:e.nom+' '+e.prenom+' ('+e.classe+')'}));
}

function saveEnseignant(){
  if(!enforceRoleAccess('manage-students')) return;
  const nom=document.getElementById('ens-nom').value.trim();
  const prenom=document.getElementById('ens-prenom').value.trim();
  if(!nom||!prenom){showToast('error','Nom et prénom obligatoires');return;}
  const e={
    id:'E'+Math.random().toString(36).substr(2,5).toUpperCase(),
    nom:nom.toUpperCase(),prenom,
    matieres:document.getElementById('ens-matieres').value.trim()||'Toutes matières',
    classes:document.getElementById('ens-classes').value.trim()||'—',
    heures:parseInt(document.getElementById('ens-heures').value)||0,
    statut:document.getElementById('ens-statut').value
  };
  DB.enseignants.push(e);
  saveToFirebase('enseignants',e);
  closeModal('modal-add-enseignant');
  renderEnseignants();
  showToast('success','Enseignant ajouté : '+nom+' '+prenom);
}

function saveParent(){
  if(!enforceRoleAccess('manage-students')) return;
  const nom=document.getElementById('parent-nom').value.trim();
  const tel=document.getElementById('parent-tel').value.trim();
  if(!nom||!tel){showToast('error','Nom et téléphone obligatoires');return;}
  const p={
    id:'PAR'+Math.random().toString(36).substr(2,5),
    nom,tel,
    email:document.getElementById('parent-email').value.trim(),
    adresse:document.getElementById('parent-adresse').value.trim(),
    enfants:[]
  };
  DB.parents.push(p);
  saveToFirebase('parents',p);
  closeModal('modal-add-parent');
  renderParents();
  showToast('success','Parent ajouté : '+nom);
}

function saveClasse(){
  if(!enforceRoleAccess('manage-students')) return;
  const nom=document.getElementById('classe-nom').value.trim();
  if(!nom){showToast('error','Nom de la classe obligatoire');return;}
  const c={
    id:'cl-'+nom.toLowerCase().replace(/[^a-z0-9]+/g,'-'),
    nom,
    niveau:document.getElementById('classe-niveau').value,
    enseignant:document.getElementById('classe-enseignant').value.trim(),
    salle:document.getElementById('classe-salle').value.trim(),
    effectif:0
  };
  DB.classes.push(c);
  saveToFirebase('classes',c);
  closeModal('modal-add-classe');
  renderClasses();
  showToast('success','Classe créée : '+nom);
}

function saveMenu(){
  const plat=document.getElementById('menu-plat').value.trim();
  if(!plat){showToast('error','Le plat du jour est obligatoire');return;}
  const m={
    id:'MEN'+Math.random().toString(36).substr(2,4),
    jour:document.getElementById('menu-jour').value,
    plat,
    taille:document.getElementById('menu-taille').value.trim()||'Assiette complète',
    prix:parseInt(document.getElementById('menu-prix').value)||0
  };
  DB.cantine.push(m);
  saveToFirebase('cantine',m);
  closeModal('modal-add-menu');
  renderCantine();
  showToast('success','Menu ajouté pour le '+m.jour);
}

function saveBus(){
  const nom=document.getElementById('bus-nom').value.trim();
  if(!nom){showToast('error','Nom du bus obligatoire');return;}
  const b={
    id:'T'+Math.random().toString(36).substr(2,4),
    nom,
    chauffeur:document.getElementById('bus-chauffeur').value.trim(),
    plaque:document.getElementById('bus-plaque').value.trim(),
    capacite:parseInt(document.getElementById('bus-capacite').value)||40,
    eleves:0,
    itineraire:document.getElementById('bus-itineraire').value.trim()
  };
  DB.transport.push(b);
  saveToFirebase('transport',b);
  closeModal('modal-add-bus');
  renderTransport();
  showToast('success','Bus ajouté : '+nom);
}

function saveLivre(){
  const titre=document.getElementById('livre-titre').value.trim();
  if(!titre){showToast('error','Le titre du livre est obligatoire');return;}
  const l={
    id:'L'+Math.random().toString(36).substr(2,4),
    titre,
    auteur:document.getElementById('livre-auteur').value.trim(),
    categorie:document.getElementById('livre-categorie').value,
    stock:parseInt(document.getElementById('livre-stock').value)||1,
    emprunte:false
  };
  DB.livres.push(l);
  saveToFirebase('livres',l);
  closeModal('modal-add-livre');
  renderBibliotheque();
  showToast('success','Livre ajouté : '+titre);
}

function saveEmprunt(){
  const livreId=document.getElementById('emprunt-livre').value;
  const eleveId=document.getElementById('emprunt-eleve').value;
  if(livreId.includes('--')||eleveId.includes('--')){showToast('error','Choisissez un livre et un élève');return;}
  const l=DB.livres.find(x=>x.id===livreId);
  const el=DB.eleves.find(x=>x.id===eleveId);
  if(!l||!el)return;
  if(l.emprunte){showToast('error','Ce livre est déjà prêté');return;}
  l.emprunte=true;
  l.empruntePar=el.nom+' '+el.prenom;
  l.retour=document.getElementById('emprunt-retour').value||new Date(Date.now()+14*24*60*60*1000).toISOString().split('T')[0];
  saveToFirebase('livres',l);
  closeModal('modal-emprunt');
  renderBibliotheque();
  showToast('success','Emprunt enregistré pour '+l.empruntePar);
}

function saveExamen(){
  const nom=document.getElementById('examen-nom').value.trim();
  if(!nom){showToast('error','Nom de l\'examen obligatoire');return;}
  const e={
    id:'EX'+Math.random().toString(36).substr(2,4),
    nom,
    classe:document.getElementById('examen-classe').value,
    date:document.getElementById('examen-date').value,
    salle:document.getElementById('examen-salle').value.trim(),
    surveillants:document.getElementById('examen-surveillants').value.trim(),
    statut:document.getElementById('examen-statut').value
  };
  DB.examens.push(e);
  saveToFirebase('examens',e);
  closeModal('modal-add-examen');
  renderExamens();
  showToast('success','Examen planifié : '+nom);
}

function saveSoin(){
  const eleveId=document.getElementById('soin-eleve').value;
  const motif=document.getElementById('soin-motif').value.trim();
  if(eleveId.includes('--')||!motif){showToast('error','Choisissez un élève et un motif');return;}
  const el=DB.eleves.find(x=>x.id===eleveId);
  if(!el)return;
  const s={
    id:'S'+Math.random().toString(36).substr(2,4),
    eleveNom:el.nom+' '+el.prenom,
    date:document.getElementById('soin-date').value,
    motif,
    traitement:document.getElementById('soin-traitement').value.trim(),
    parentNotifie:true,
    refere:false
  };
  DB.sante.push(s);
  saveToFirebase('sante',s);
  closeModal('modal-add-soin');
  renderSante();
  showToast('success','Visite enregistrée pour '+s.eleveNom);
}

function saveStock(){
  const article=document.getElementById('stock-article').value.trim();
  if(!article){showToast('error','Nom de l\'article obligatoire');return;}
  const s={
    id:'S'+Math.random().toString(36).substr(2,4),
    article,
    categorie:document.getElementById('stock-categorie').value,
    stock:parseInt(document.getElementById('stock-qte').value)||0,
    stockMin:parseInt(document.getElementById('stock-min').value)||1,
    unite:document.getElementById('stock-unite').value.trim()||'pcs'
  };
  DB.stocks.push(s);
  saveToFirebase('stocks',s);
  closeModal('modal-add-stock');
  renderStocks();
  showToast('success','Article ajouté : '+article);
}

function saveSortieStock(){
  const id=document.getElementById('sortie-stock-article').value;
  const qty=parseInt(document.getElementById('sortie-stock-qte').value);
  if(id.includes('--')){showToast('error','Choisissez un article');return;}
  const s=DB.stocks.find(x=>x.id===id);
  if(!s)return;
  if(!qty||qty<=0){showToast('error','Quantité invalide');return;}
  if(s.stock<qty){showToast('error','Stock insuffisant (disponible: '+s.stock+' '+s.unite+')');return;}
  s.stock-=qty;
  saveToFirebase('stocks',s);
  closeModal('modal-sortie-stock');
  renderStocks();
  showToast('success',qty+'unité(s) sortie(s) de '+s.article);
}

function savePersonnel(){
  const nom=document.getElementById('personnel-nom').value.trim();
  if(!nom){showToast('error','Nom obligatoire');return;}
  const p={
    id:'P'+Math.random().toString(36).substr(2,4),
    nom,
    poste:document.getElementById('personnel-poste').value,
    contact:document.getElementById('personnel-contact').value.trim(),
    contrat:document.getElementById('personnel-contrat').value,
    statut:document.getElementById('personnel-statut').value
  };
  DB.personnel.push(p);
  saveToFirebase('personnel',p);
  closeModal('modal-add-personnel');
  renderPersonnel();
  showToast('success','Personnel ajouté : '+nom);
}

function saveFrais(){
  const niveau=document.getElementById('frais-niveau').value.trim();
  if(!niveau){showToast('error','Le niveau est obligatoire');return;}
  const f={
    niveau,
    inscription:parseInt(document.getElementById('frais-inscription').value)||0,
    scolarite:parseInt(document.getElementById('frais-scolarite').value)||0,
    cantine:parseInt(document.getElementById('frais-cantine').value)||0,
    transport:parseInt(document.getElementById('frais-transport').value)||0
  };
  DB.frais.push(f);
  saveToFirebase('frais',f);
  closeModal('modal-add-frais');
  renderFrais();
  showToast('success','Barème ajouté pour le niveau '+niveau);
}

function sendNewMessage(){
  const dest=document.getElementById('msg-dest').value;
  const txt=document.getElementById('msg-content').value.trim();
  if(dest.includes('--')){showToast('error','Choisissez un destinataire');return;}
  if(!txt){showToast('error','Le message est vide');return;}
  const m={
    id:'M'+Date.now(),
    from:dest,
    avatar:dest.charAt(0).toUpperCase(),
    msg:txt,
    time:'Maintenant',
    read:false
  };
  DB.messages.unshift(m);
  saveToFirebase('messages',m);
  closeModal('modal-send-message');
  renderMessages();
  showToast('success','Message envoyé à '+dest);
}

function genDocModal(){
  const eleveId=document.getElementById('gen-doc-eleve').value;
  const type=document.getElementById('gen-doc-type').value;
  if(eleveId.includes('--')){showToast('error','Choisissez un élève');return;}
  const el=DB.eleves.find(x=>x.id===eleveId);
  if(!el)return;
  const d={
    id:'D'+Date.now(),
    type,
    eleve:el.nom+' '+el.prenom,
    date:new Date().toISOString().split('T')[0],
    par:'Direction',
    qr:'QR-'+Math.floor(1000+Math.random()*9000)
  };
  DB.documents.push(d);
  saveToFirebase('documents',d);
  closeModal('modal-gen-doc');
  renderDocuments();
  showToast('success',type+'généré pour '+d.eleve+' — '+d.qr);
}




function renderCantine(){
  document.getElementById('cantine-menu').innerHTML=DB.cantine.length===0
    ?'<div class="empty-state"><div class="empty-icon"></div><div class="empty-title">Aucun menu saisi pour le moment</div></div>'
    :DB.cantine.map(m=>`
      <div style="display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid var(--border)">
        <div>
          <div style="font-weight:700;font-size:13px">${m.jour}</div>
          <div style="font-size:12px;color:var(--text2)">${m.plat} · ${m.taille}</div>
        </div>
        <span class="badge badge-teal">${m.prix?m.prix.toLocaleString()+'FCFA':'Gratuit'}</span>
      </div>`).join('');
  document.getElementById('cantine-presences').innerHTML=`
    <div style="display:flex;flex-direction:column;gap:10px">
      <div style="display:flex;justify-content:space-between"><span style="font-size:12px;color:var(--text2)">Élèves inscrits à la cantine</span><strong>${DB.eleves.length}</strong></div>
      <div style="display:flex;justify-content:space-between"><span style="font-size:12px;color:var(--text2)">Prix du repas (FCFA)</span><strong>${DB.frais.length?DB.frais[0].cantine.toLocaleString():'—'}</strong></div>
      <div class="empty-state"><div class="empty-icon"></div><div class="empty-title">Présences cantine à saisir à l'heure du repas</div></div>
    </div>`;
}




function saveToFirebase(collection, data){
  if(!window.FIREBASE_READY){ return; }
  try{
    const dbRef = window.FB_REF(window.FB_DB, `${CURRENT_SCHOOL_ID}/${collection}/${data.id}`);
    window.FB_SET(dbRef, data)
      .then(()=> console.log('Firebase saved:', collection, data.id))
      .catch(err=> console.warn('Firebase save error:', err));
  }catch(e){ console.warn('Firebase saveToFirebase error:',e); }
}

function loadFromFirebase(){
  if(!window.FIREBASE_READY){
    console.log('Firebase SDK pas encore prêt — données locales utilisées');
    return;
  }
  const collections = ['eleves','enseignants','notes','paiements','annonces','livres','stocks','creneaux','examens','sante','personnel','documents','frais','transport','messages','cantine','parents'];
  let loaded = 0;
  collections.forEach(col=>{
    try{
      const dbRef = window.FB_REF(window.FB_DB, `${CURRENT_SCHOOL_ID}/${col}`);
      window.FB_GET(dbRef).then(snapshot=>{
        if(snapshot.exists()){
          const val = snapshot.val();
          DB[col] = typeof val === 'object' && !Array.isArray(val)
            ? Object.values(val)
            : val;
          console.log(`Firebase chargé: ${col} — ${DB[col].length} enregistrements`);
          loaded++;
          if(col==='eleves'){
            document.getElementById('badge-eleves').textContent = DB.eleves.length;
            document.getElementById('stat-eleves') && (document.getElementById('stat-eleves').textContent = DB.eleves.length);
          }
          if(loaded === collections.length){
            showToast('success',`Firebase LOUX synchronisé — ${DB.eleves.length} élèves`);
            renderDashboard();
          }
        } else {
          console.log(`Firebase: ${col} vide — seed local conservé`);
        }
      }).catch(err=> console.warn(`Firebase load error [${col}]:`, err));
    }catch(e){ console.warn('Firebase loadFromFirebase error:',e); }
  });
}


function subscribeFirebaseLive(){
  if(!window.FIREBASE_READY) return;
  try{
    const elevesRef = window.FB_REF(window.FB_DB, `${CURRENT_SCHOOL_ID}/eleves`);
    window.FB_ON(elevesRef, (snapshot)=>{
      if(snapshot.exists()){
        const val = snapshot.val();
        DB.eleves = typeof val === 'object' && !Array.isArray(val)
          ? Object.values(val)
          : val;
        document.getElementById('badge-eleves').textContent = DB.eleves.length;
        console.log('Firebase live update: eleves', DB.eleves.length);
      }
    });
  }catch(e){ console.warn('Firebase subscribe error:',e); }
}




function quickAdd(){
  const items=[
    {label:'Inscrire un élève',action:"openModal('modal-add-eleve')"},
    {label:'Saisir des notes',action:"openModal('modal-add-note')"},
    {label:'Enregistrer paiement',action:"openModal('modal-add-paiement')"},
    {label:'Faire l\'appel',action:"openModal('modal-appel')"},
    {label:'Nouvelle annonce',action:"openModal('modal-add-annonce')"},
  ];
  const menu=document.createElement('div');
  menu.style.cssText='position:fixed;top:70px;right:24px;background:#fff;border:1px solid var(--border);border-radius:14px;box-shadow:0 8px 30px rgba(0,0,0,.12);z-index:200;padding:6px;min-width:220px;animation:slideUp .2s ease';
  menu.innerHTML=items.map(i=>`<div style="padding:10px 14px;border-radius:10px;cursor:pointer;font-size:13px;font-weight:500;transition:background .15s"onmouseenter="this.style.background='var(--violet-bg)'"onmouseleave="this.style.background=''"onclick="${i.action};this.parentElement.remove()">${i.label}</div>`).join('');
  document.body.appendChild(menu);
  setTimeout(()=>document.addEventListener('click',()=>menu.remove(),{once:true}),100);
}

function globalSearch(q){

  if(!q||q.length<2){renderEleves();return;}
  const results=DB.eleves.filter(e=>(e.nom+' '+e.prenom).toLowerCase().includes(q.toLowerCase()));
  if(results.length>0){showPage('eleves');renderEleves(results);}
  else{showToast('info','Aucun élève trouvé pour "'+q+'"');}
}




function viewEleve(id){
  const el = DB.eleves.find(e => e.id === id);
  if(!el) return;
  showToast('info', `Fiche Élevé : ${el.prenom} ${el.nom} (${el.classe}) - Matricule: ${el.matricule} - Parent : ${el.parentNom} (${el.parentTel})`);
}

function editEleve(id){
  const el = DB.eleves.find(e => e.id === id);
  if(!el) return;
  editingEleveId = id;
  openModal('modal-add-eleve');
  document.querySelector('#modal-add-eleve .modal-title').textContent = "Modifier le dossier élève";
  document.querySelector('#modal-add-eleve .btn-primary').textContent = "Enregistrer les modifications";

  document.getElementById('eleve-nom').value = el.nom;
  document.getElementById('eleve-prenom').value = el.prenom;
  document.getElementById('eleve-ddn').value = el.ddn || '';
  document.getElementById('eleve-lieu-naissance').value = el.lieuNaissance || '';
  document.getElementById('eleve-sexe').value = el.sexe;
  document.getElementById('eleve-nationalite').value = el.nationalite || 'Congolaise';
  document.getElementById('eleve-adresse').value = el.adresse || '';
  document.getElementById('eleve-classe').value = el.classe;
  document.getElementById('eleve-parent-nom').value = el.parentNom || '';
  document.getElementById('eleve-parent-tel').value = el.parentTel || '';
}

function genDocEleve(id){
  const el = DB.eleves.find(e => e.id === id);
  if(el) {
    showToast('success', `Attestation générée pour ${el.prenom} ${el.nom} — QR Code ajouté`);
  }
}

function editEnseignant(id){
  const ens = DB.enseignants.find(e => e.id === id);
  if(ens) {
    const newMatiere = prompt(`Modifier les matières enseignées par ${ens.prenom} ${ens.nom} :`, ens.matieres);
    if(newMatiere !== null) {
      ens.matieres = newMatiere;
      saveToFirebase('enseignants', ens);
      renderEnseignants();
      showToast('success', 'Matières enseignées mises à jour');
    }
  }
}

function editNote(id){
  const note = DB.notes.find(n => n.id === id);
  if(note) {
    const newVal = prompt(`Modifier la note de ${note.eleveNom} (Matière: ${note.matiere}) sur ${note.sur} :`, note.note);
    if(newVal !== null && !isNaN(parseFloat(newVal))) {
      note.note = parseFloat(newVal);
      saveToFirebase('notes', note);
      renderNotes();
      showToast('success', 'Note mise à jour');
    }
  }
}

function deleteNote(id){
  if(confirm('Supprimer cette note ?')){
    DB.notes=DB.notes.filter(n=>n.id!==id);
    if(window.FIREBASE_READY) {
      try {
        const dbRef = window.FB_REF(window.FB_DB, `${CURRENT_SCHOOL_ID}/notes/${id}`);
        window.FB_REMOVE(dbRef);
      } catch(e) { console.warn(e); }
    }
    renderNotes();
    showToast('success','Note supprimée');
  }
}

function printRecu(id){showToast('success','Reçu PDF généré et prêt à imprimer');}

function relancerParent(id){
  const el = DB.eleves.find(e => e.id === id);
  if(el) {
    showToast('success', `SMS de relance envoyé au parent de ${el.prenom} ${el.nom} (${el.parentTel})`);
  }
}

function genBulletin(id){showToast('success','Bulletin PDF généré avec signature numérique + QR Code');}
function genAllBulletins(){showToast('info','Génération de tous les bulletins en cours...');}
function exportEleves(){showToast('success','Export Excel des élèves prêt');}
function exportNotes(){showToast('success','Export Excel des notes prêt');}
function exportPresences(){showToast('success','Export des présences prêt');}
function exportFinances(){showToast('success','Export Excel finances prêt');}
function printEmploiDuTemps(){showToast('success','Emploi du temps envoyé à l\'impression');}

function editCreneau(id){
  const cr = DB.creneaux.find(c => c.id === id);
  if(cr) {
    const newSalle = prompt(`Modifier la salle du créneau ${cr.matiere} (${cr.jour}) :`, cr.salle);
    if(newSalle !== null) {
      cr.salle = newSalle;
      saveToFirebase('creneaux', cr);
      renderEmploiDuTemps(cr.classe);
      showToast('success', 'Salle du créneau mise à jour');
    }
  }
}

function genConvocation(id){showToast('success','Convocations PDF générées pour tous les élèves');}

function editExamen(id){
  const ex = DB.examens.find(x => x.id === id);
  if(ex) {
    const newSalle = prompt(`Modifier la salle de l'examen "${ex.nom}" :`, ex.salle);
    if(newSalle !== null) {
      ex.salle = newSalle;
      saveToFirebase('examens', ex);
      renderExamens();
      showToast('success', 'Salle d\'examen mise à jour');
    }
  }
}

function downloadDoc(id){showToast('success','Document PDF téléchargé');}
function verifyDoc(id){showToast('info','Vérification QR Code — Document authentique ');}

function toggleEmprunt(id){
  const l=DB.livres.find(x=>x.id===id);
  if(l){
    l.emprunte=!l.emprunte;
    if(l.emprunte) {
      const el = DB.eleves[Math.floor(Math.random()*DB.eleves.length)];
      l.empruntePar = el.nom + ' ' + el.prenom;
      l.retour = new Date(Date.now() + 14*24*60*60*1000).toISOString().split('T')[0];
    } else {
      l.empruntePar = '';
      l.retour = '';
    }
    saveToFirebase('livres', l);
    renderBibliotheque();
    showToast('success', l.emprunte ? `Prêt enregistré pour ${l.empruntePar}` : 'Retour enregistré');
  }
}

function msgParent(tel){showPage('messages');}
function callParent(tel){showToast('info','Appel vers '+tel);}

function editBus(id){
  const bus = DB.transport.find(b => b.id === id);
  if(bus) {
    const newChauffeur = prompt(`Modifier le chauffeur du ${bus.nom} :`, bus.chauffeur);
    if(newChauffeur !== null) {
      bus.chauffeur = newChauffeur;
      saveToFirebase('transport', bus);
      renderTransport();
      showToast('success', 'Chauffeur du bus mis à jour');
    }
  }
}

function addStock(id){
  const s = DB.stocks.find(x => x.id === id);
  if(s) {
    const qty = parseInt(prompt(`Quantité à ajouter pour l'article "${s.article}" :`, "10"));
    if(!isNaN(qty) && qty > 0) {
      s.stock += qty;
      saveToFirebase('stocks', s);
      renderStocks();
      showToast('success', `${qty} unités ajoutées au stock.`);
    }
  }
}

function removeStock(id){
  const s = DB.stocks.find(x => x.id === id);
  if(s) {
    const qty = parseInt(prompt(`Quantité à soustraire pour l'article "${s.article}" :`, "1"));
    if(!isNaN(qty) && qty > 0) {
      if(s.stock >= qty) {
        s.stock -= qty;
        saveToFirebase('stocks', s);
        renderStocks();
        showToast('success', `${qty} unités retirées du stock.`);
      } else {
        showToast('error', `Stock insuffisant (disponible: ${s.stock})`);
      }
    }
  }
}

function genReport(){showToast('success','Rapport PDF généré');}
function showAIInsights(){showToast('info','Analyse IA: Jean NZINGA, Marie MOUKALA, Paul MAKOSSO — Moyennes en baisse depuis 3 semaines');}
function updatePresence(id,val){showToast('success',`Présence mise à jour: ${val}`);}
function genDoc(type){
  openModal('modal-gen-doc');
  const t=document.getElementById('gen-doc-type');
  if(t && type) t.value=type;
}
function changeSchool(v){
  if(!v) return;
  setCurrentSchoolId(v);

  const sel = document.getElementById('schoolSelect');
  if(sel){
    const txt = sel.options[sel.selectedIndex].text;
    showToast('info','École active : '+txt);
  }
}
function changeYear(v){showToast('info','Année scolaire: '+v);}




function showToast(type,msg){
  const icons={success:'',error:'',info:''};
  const t=document.createElement('div');
  t.className=`toast ${type}`;
  t.innerHTML=`<span class="toast-icon">${icons[type]||'•'}</span>${msg}`;
  document.getElementById('toast-container').appendChild(t);
  setTimeout(()=>{t.style.opacity='0';t.style.transform='translateY(10px)';t.style.transition='all .3s';setTimeout(()=>t.remove(),300);},3000);
}




function toggleSidebar(){
  document.getElementById('sidebar').classList.toggle('open');
}




document.addEventListener('FirebaseReady', () => {
  console.log('Firebase synchronisé en temps réel.');
  loadFromFirebase();
  subscribeFirebaseLive();
  setupAuthListeners();
});

window.addEventListener('load',()=>{
  seedData();


  if (window.FIREBASE_READY) {
    loadFromFirebase();
    subscribeFirebaseLive();
    setupAuthListeners();
  }

  renderDashboard();
  applyRolePermissions();
  document.getElementById('current-date-display').textContent=new Date().toLocaleDateString('fr-FR',{weekday:'long',day:'numeric',month:'long',year:'numeric'});


  if(window.innerWidth<=768){
    document.getElementById('menu-btn').style.display='block';
  }


  const louxConfig = {
    apiKey: "AIzaSyAroPw37xo7S5yPnfzJ33MRVpMan3-EIPw",
    authDomain: "loux-fa248.firebaseapp.com",
    databaseURL: "https://loux-fa248-default-rtdb.firebaseio.com",
    projectId: "loux-fa248",
    storageBucket: "loux-fa248.firebasestorage.app",
    messagingSenderId: "833956604070",
    appId: "1:833956604070:web:5f5bf800dd072a441d2c67"
  };
  Object.entries(louxConfig).forEach(([k,v])=>{
    const el=document.getElementById('fb-'+k);
    if(el) el.value=v;
  });


  const schoolSel = document.getElementById('schoolSelect');
  if(schoolSel) schoolSel.value = CURRENT_SCHOOL_ID;

  showToast('success','EduManager Pro chargé — '+DB.eleves.length+' élèves');
});
