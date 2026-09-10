import {
    createUserWithEmailAndPassword,
    signInWithEmailAndPassword,
    signOut,
    onAuthStateChanged
} from "firebase/auth";

import {
    doc,
    getDoc,
    setDoc,
    serverTimestamp
} from "firebase/firestore";

import { auth, db } from "../firebase";


// ========================================
// REGISTER USER
// ========================================

export const registerUser = async (
    username,
    email,
    password,
    role
) => {

    // Create account in Firebase Authentication
    const userCredential =
        await createUserWithEmailAndPassword(
            auth,
            email,
            password
        );

    const user = userCredential.user;

    // Store additional user information in Firestore
    await setDoc(
        doc(db, "users", user.uid),
        {
            username: username,
            email: email,
            role: role,
            createdAt: serverTimestamp()
        }
    );

    return user;
};


// ========================================
// LOGIN USER
// ========================================

export const loginUser = async (
    email,
    password
) => {

    // Firebase automatically validates
    // the email and password.
    const userCredential =
        await signInWithEmailAndPassword(
            auth,
            email,
            password
        );

    return userCredential.user;
};


// ========================================
// GET USER PROFILE
// ========================================

export const getUserProfile = async (uid) => {

    const userDocument = await getDoc(
        doc(db, "users", uid)
    );

    if (userDocument.exists()) {
        return userDocument.data();
    }

    return null;
};


// ========================================
// LOGOUT USER
// ========================================

export const logoutUser = async () => {
    await signOut(auth);
};


// ========================================
// AUTHENTICATION STATE LISTENER
// ========================================

export const subscribeToAuthChanges = (
    callback
) => {

    return onAuthStateChanged(
        auth,
        callback
    );
};