import os
import cv2
import numpy as np
import mediapipe as mp
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import joblib

import mediapipe as mp

# Initialize MediaPipe Pose
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(static_image_mode=True, min_detection_confidence=0.5)

def extract_keypoints(image):
    """ Extracts 33 keypoints using MediaPipe """
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = pose.process(image_rgb)
    
    if not results.pose_landmarks:
        return np.zeros(33 * 3) # Return zeros if no pose detected
    
    # Flatten landmarks to [33 * 3] -> [x, y, visibility]
    keypoints = []
    for lm in results.pose_landmarks.landmark:
        keypoints.extend([lm.x, lm.y, lm.visibility])
        
    return np.array(keypoints)

def collect_data(data_dir):
    """ 
    Expects data_dir to have subfolders for each class (e.g., 'squat_up', 'squat_down')
    containing images.
    """
    X = []
    y = []
    classes = os.listdir(data_dir)
    
    for label, class_name in enumerate(classes):
        class_dir = os.path.join(data_dir, class_name)
        for img_name in os.listdir(class_dir):
            img_path = os.path.join(class_dir, img_name)
            image = cv2.imread(img_path)
            if image is not None:
                features = extract_keypoints(image)
                X.append(features)
                y.append(label)
                
    return np.array(X), np.array(y), classes

def train():
    data_dir = "pose_dataset" # User should provide this
    if not os.path.exists(data_dir):
        print(f"Please create a '{data_dir}' folder with class subdirectories.")
        return

    print("Extracting features...")
    X, y, classes = collect_data(data_dir)
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
    
    print("Training Random Forest model...")
    model = RandomForestClassifier(n_estimators=100)
    model.fit(X_train, y_train)
    
    accuracy = model.score(X_test, y_test)
    print(f"Model trained with accuracy: {accuracy * 100:.2f}%")
    
    # Save model and class list
    joblib.dump(model, "pose_classifier.pkl")
    joblib.dump(classes, "pose_classes.pkl")
    print("Model saved as pose_classifier.pkl")

if __name__ == "__main__":
    # You need to have a dataset first!
    # train()
    print("MediaPipe Training Template Ready. Populate 'pose_dataset/' to begin training.")
