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
    role = "user"
) => {
    const userCredential =
        await createUserWithEmailAndPassword(
            auth,
            email,
            password
        );

    const user = userCredential.user;

    await setDoc(
        doc(db, "users", user.uid),
        {
            username,
            email,
            role,
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
    if (!uid) {
        return null;
    }

    const userDocument = await getDoc(
        doc(db, "users", uid)
    );

    if (!userDocument.exists()) {
        return null;
    }

    const profile = userDocument.data();

    return {
        ...profile,
        role: profile.role || "user"
    };
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

export const subscribeToAuthChanges = (callback) => {
    return onAuthStateChanged(
        auth,
        callback
    );
};