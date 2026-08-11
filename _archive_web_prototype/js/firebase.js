  import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-app.js";
  import { getDatabase, ref, set, get, onValue, push, remove } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-database.js";
    import { getAuth, createUserWithEmailAndPassword, signInWithEmailAndPassword, signOut, onAuthStateChanged, updateProfile } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-auth.js";

  const firebaseConfig = {
    apiKey: "AIzaSyAroPw37xo7S5yPnfzJ33MRVpMan3-EIPw",
    authDomain: "loux-fa248.firebaseapp.com",
    databaseURL: "https://loux-fa248-default-rtdb.firebaseio.com",
    projectId: "loux-fa248",
    storageBucket: "loux-fa248.firebasestorage.app",
    messagingSenderId: "833956604070",
    appId: "1:833956604070:web:5f5bf800dd072a441d2c67",
    measurementId: "G-R9RQ7V8S2G"
  };

  const app = initializeApp(firebaseConfig);
  const db = getDatabase(app);

    const auth = getAuth(app);


  window.FB_DB = db;
  window.FB_REF = ref;
  window.FB_SET = set;
  window.FB_GET = get;
  window.FB_ON = onValue;
  window.FB_PUSH = push;
  window.FB_REMOVE = remove;
    window.FB_AUTH = auth;
    window.FB_CREATE_USER = createUserWithEmailAndPassword;
    window.FB_SIGNIN = signInWithEmailAndPassword;
    window.FB_SIGNOUT = signOut;
    window.FB_ONAUTH = onAuthStateChanged;
  window.FIREBASE_READY = true;

  console.log('Firebase LOUX initialisé');

  document.dispatchEvent(new CustomEvent('FirebaseReady'));
