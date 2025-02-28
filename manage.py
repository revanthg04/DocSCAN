from website import create_app, db
import os
import mimetypes
from website.models import Document2, User

app = create_app()

def create_admins():
    admin_emails = ["grev@gmail.com"]
    with app.app_context():
        for email in admin_emails:
            user = User.query.filter_by(email=email).first()
            if user and not user.is_admin:
                user.is_admin = True
        db.session.commit()
    print("Admins assigned successfully!")

def upload_files_from_folder(folder_path, user_id):
    """Uploads all files from a given folder to Document2."""
    if not os.path.exists(folder_path):
        print(f"Folder '{folder_path}' does not exist.")
        return

    with app.app_context():  # ✅ Use 'app' instead of 'current_app'
        user = User.query.get(user_id)
        if not user:
            print("User not found.")
            return
        
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):
                mime_type, _ = mimetypes.guess_type(file_path)
                mime_type = mime_type if mime_type else "application/octet-stream"

                with open(file_path, "rb") as file:
                    file_data = file.read()

                new_document = Document2(
                    user_id=user_id,
                    filename=filename,
                    mime_type=mime_type,
                    file_data=file_data
                )
                db.session.add(new_document)
        
        db.session.commit()
        print(f"All files from '{folder_path}' uploaded successfully.")

if __name__ == "__main__":
    with app.app_context():  # ✅ Ensure app context is set before calling functions
        create_admins()
        upload_files_from_folder("C:/Users/galam/Desktop/Cathgo/Database", user_id=1)
