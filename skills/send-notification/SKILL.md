---
name: send-notification
description: Generates a professional company team announcement email based on structured input. Use this skill when the user wants to send a notification, announcement, or email update to a team or the company.
---

# Send Notification

## Instructions

1.  **Gather Information**: Ensure you have the following three pieces of information from the user. If any are missing, ask the user for them specifically:
    *   **Who should read this message?** (Target audience)
    *   **What is happening?** (The core event, context, and details)
    *   **What should you do?** (Action items for the audience)

2.  **Draft the Email**: Generate an email in English using a professional, corporate tone.
    *   **Subject Line**: Create a clear, concise subject line starting with a tag like `[Announcement]`, `[Update]`, or `[Action Required]`.
    *   **Structure**:
        *   **Who should read this message?**: Clearly state the audience.
        *   **What is happening?**: Describe the event/update in detail. Include dates, times, and impact if applicable.
        *   **What should you do?**: Provide clear instructions or "None" if informational only.
        *   **Contact Info**: Add a standard footer asking users to contact a specific channel or person if they have questions (you can ask the user for this if not provided, or use a placeholder like "[Team Name] Support").

3.  **Format**: Use the following format as a template:

    ```text
    Subject: [Announcement] <Concise Subject>

    Who should read this message?
    <Target Audience>

    What is happening?
    <Detailed description of the event. Use paragraphs for readability.>

    <If applicable: Maintenance Window / Specific Dates>
    <Date/Time Range>

    What should you do?
    <Action items>

    Who to contact if you have questions?
    If you have any questions or concerns, please contact us on Slack at <Channel> or email <Email>. We are here to assist you.
    ```

4.  **Review**: Ensure the tone is polite, clear, and grammatically correct English.
