import cv2
import mediapipe as mp
import numpy as np
import pyautogui
import webbrowser
import time
import os

# Initialize Mediapipe hands
mp_hands = mp.solutions.hands
hands = mp_hands.Hands()
mp_drawing = mp.solutions.drawing_utils

# Capture video from webcam
cap = cv2.VideoCapture(0)

screen_width, screen_height = pyautogui.size()

# Variables to store the last recognized gesture and timestamp
last_gesture_id = None
last_gesture_time = 0
last_shortcut_time = 0  # Timestamp for the last executed shortcut
cooldown_period = 2  # Cooldown period for gesture mode toggle in seconds
shortcut_interval = 5  # Interval between shortcuts in seconds
shortcuts_state = 0  # 0: inactive, 1: active, 2: completely deactivated

def open_website(gesture_id):
    websites = {
        1: "https://www.google.com",
        2: "https://www.facebook.com",
        3: "https://www.youtube.com",
        4: "https://www.netflix.com/in/"
    }
    if gesture_id in websites:
        webbrowser.open(websites[gesture_id])

def recognize_gesture(landmarks):
    # Simple gesture recognition based on relative positions of landmarks
    thumb_tip = landmarks[mp_hands.HandLandmark.THUMB_TIP]
    index_finger_tip = landmarks[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    middle_finger_tip = landmarks[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
    ring_finger_tip = landmarks[mp_hands.HandLandmark.RING_FINGER_TIP]
    pinky_tip = landmarks[mp_hands.HandLandmark.PINKY_TIP]

    # Example gestures
    if thumb_tip.y > ring_finger_tip.y:
        return 1  # Gesture 1 (e.g., open Google)
    elif pinky_tip.y > middle_finger_tip.y:
        return 2  # Gesture 2 (e.g., open Facebook)
    elif pinky_tip.y > thumb_tip.y:
        return 3  # Gesture 3 (e.g., open YouTube)
    elif index_finger_tip.y < ring_finger_tip.y and index_finger_tip.y < middle_finger_tip.y:
        return 4  # Gesture 4 (e.g., open Netflix)
    elif thumb_tip.y < index_finger_tip.y < middle_finger_tip.y:  # New gesture for toggling shortcuts
        return 5  # Gesture 5 (e.g., toggle shortcuts)
    elif thumb_tip.x < pinky_tip.x:  # New gesture for deactivating shortcuts
        return 6  # Gesture 6 (e.g., deactivate shortcuts)
    elif thumb_tip.x > index_finger_tip.x and index_finger_tip.x > middle_finger_tip.x:  # New gesture for volume up
        return 7  # Gesture 7 (e.g., volume up)
    elif index_finger_tip.x > thumb_tip.x and thumb_tip.x > middle_finger_tip.x:  # New gesture for volume down
        return 8  # Gesture 8 (e.g., volume down)
    return 0  # No recognizable gesture

def control_volume(gesture_id):
    if gesture_id == 7:
        # Increase volume by one notch
        os.system("osascript -e 'set volume output volume (output volume of (get volume settings) + 10)'")
    elif gesture_id == 8:
        # Decrease volume by one notch
        os.system("osascript -e 'set volume output volume (output volume of (get volume settings) - 10)'")

def main():
    global last_gesture_id, last_gesture_time, last_shortcut_time, shortcuts_state
    notification_start_time = None
    notification_duration = 5  # Duration for which the notification is displayed (in seconds)
    notification_message = ""

    # FPS calculation variables
    frame_count = 0
    start_time = time.time()

    while cap.isOpened():
        success, image = cap.read()
        if not success:
            print("Ignoring empty camera frame.")
            continue

        # Increment frame count
        frame_count += 1

        # Calculate FPS
        elapsed_time = time.time() - start_time
        fps = frame_count / elapsed_time

        # Flip the image horizontally for a later selfie-view display, and convert the color space from BGR to RGB
        image = cv2.flip(image, 1)
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Process the image and detect hands
        results = hands.process(image_rgb)

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                # Extract landmark coordinates
                landmarks = hand_landmarks.landmark
                index_finger_tip = landmarks[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                index_finger_pip = landmarks[mp_hands.HandLandmark.INDEX_FINGER_PIP]

                # Convert coordinates to screen size
                x = int(index_finger_tip.x * screen_width)
                y = int(index_finger_tip.y * screen_height)

                # Move the mouse
                pyautogui.moveTo(x, y)

                # Detect click gesture (distance between index finger tip and PIP)
                distance = np.sqrt((index_finger_tip.x - index_finger_pip.x) ** 2 +
                                   (index_finger_tip.y - index_finger_pip.y) ** 2 +
                                   (index_finger_tip.z - index_finger_pip.z) ** 2)

                # Click if the distance is below a threshold
                if distance < 0.02:
                    pyautogui.click()

                # Recognize gesture and perform actions
                gesture_id = recognize_gesture(landmarks)
                current_time = time.time()

                if gesture_id == 5 and (current_time - last_gesture_time > cooldown_period):
                    if shortcuts_state != 2:  # Only toggle if not completely deactivated
                        shortcuts_state = 1 if shortcuts_state == 0 else 0
                        notification_message = "Gesture Mode: Activated" if shortcuts_state == 1 else "Gesture Mode: Deactivated"
                        notification_start_time = current_time
                    last_gesture_time = current_time

                elif gesture_id == 6 and (current_time - last_gesture_time > cooldown_period):
                    shortcuts_state = 2  # Completely deactivate shortcuts
                    notification_message = "Gesture Mode: Completely Deactivated"
                    notification_start_time = current_time
                    last_gesture_time = current_time

                if shortcuts_state == 1 and gesture_id and gesture_id != last_gesture_id:
                    if gesture_id != 5 and gesture_id != 6 and (current_time - last_shortcut_time > shortcut_interval):  # Avoid triggering website for toggle gestures and check interval
                        if gesture_id in [1, 2, 3, 4]:
                            open_website(gesture_id)
                        elif gesture_id in [7, 8]:
                            control_volume(gesture_id)
                        last_shortcut_time = current_time
                    last_gesture_id = gesture_id
                    last_gesture_time = current_time

        # Display notification if within the duration
        if notification_start_time and (time.time() - notification_start_time < notification_duration):
            cv2.putText(image, notification_message, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

        # Add constant notification for gesture mode activation
        if shortcuts_state == 1:
            cv2.putText(image, 'Gesture Mode: Active', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
        elif shortcuts_state == 0:
            cv2.putText(image, 'Gesture Mode: Inactive', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)
        elif shortcuts_state == 2:
            cv2.putText(image, 'Gesture Mode: Completely Deactivated', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2, cv2.LINE_AA)

        # Display FPS on the image
        cv2.putText(image, f'FPS: {fps:.2f}', (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2, cv2.LINE_AA)

        # Display the image
        cv2.imshow('Hand Gesture Mouse Control', image)
        if cv2.waitKey(5) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()