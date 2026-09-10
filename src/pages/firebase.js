// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
import { getFirestore } from "firebase/firestore";
import { getAuth } from "firebase/auth";
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
    apiKey: "AIzaSyDGcGkp0mNvnGhrB5XLYUHL0spbNPyV7PE",
    authDomain: "standiq-db33c.firebaseapp.com",
    projectId: "standiq-db33c",
    storageBucket: "standiq-db33c.firebasestorage.app",
    messagingSenderId: "439210062522",
    appId: "1:439210062522:web:803d109fc60909507c8883",
    measurementId: "G-5TXNWJ1M5R"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

const analytics = getAnalytics(app);
const db = getFirestore(app);
const auth = getAuth(app);

export { app, analytics, db, auth };