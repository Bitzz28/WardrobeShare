// Verification Functions
function requestVerification(type) {
    const modal = document.getElementById('verificationModal');
    const title = document.getElementById('verificationTitle');
    const description = document.getElementById('verificationDescription');
    const fields = document.getElementById('verificationFields');
    const typeInput = document.getElementById('verificationType');

    typeInput.value = type;

    switch(type) {
        case 'govt_id':
            title.textContent = 'Request Government ID';
            description.textContent = 'Please provide a clear photo of your government-issued ID.';
            fields.innerHTML = `
                <div>
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">ID Document</label>
                    <input type="file" name="id_document" accept="image/*,.pdf" required class="mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100">
                </div>
            `;
            break;
        case 'selfie':
            title.textContent = 'Request Selfie';
            description.textContent = 'Please provide a clear selfie for verification.';
            fields.innerHTML = `
                <div>
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Selfie Photo</label>
                    <input type="file" name="selfie" accept="image/*" required class="mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100">
                </div>
            `;
            break;
        case 'personal_details':
            title.textContent = 'Request Personal Details';
            description.textContent = 'Please provide your personal information.';
            fields.innerHTML = `
                <div class="space-y-4">
                    <div>
                        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Full Name</label>
                        <input type="text" name="full_name" required class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Contact Number</label>
                        <input type="tel" name="contact_number" required class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Address</label>
                        <textarea name="address" rows="3" required class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"></textarea>
                    </div>
                </div>
            `;
            break;
    }

    modal.classList.remove('hidden');
}

function closeVerificationModal() {
    document.getElementById('verificationModal').classList.add('hidden');
}

// Handle verification form submission
document.getElementById('verificationForm').addEventListener('submit', function(e) {
    e.preventDefault();
    const formData = new FormData(this);
    formData.append('chat_room_id', chatRoomId);

    fetch('/chat/request-verification/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            closeVerificationModal();
            // Add success message to chat
            const messageHtml = `
                <div class="flex justify-end mb-4">
                    <div class="bg-blue-500 text-white rounded-lg p-3 max-w-[70%] shadow">
                        <p class="text-sm">Verification request sent successfully.</p>
                    </div>
                </div>
            `;
            document.getElementById('chat-messages').insertAdjacentHTML('beforeend', messageHtml);
            scrollToBottom();
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
});

// Handle rental terms form submission
document.getElementById('rentalTermsForm').addEventListener('submit', function(e) {
    e.preventDefault();
    const formData = new FormData(this);
    formData.append('chat_room_id', chatRoomId);

    fetch('/chat/set-rental-terms/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            document.getElementById('rentalTermsModal').style.display = 'none';
            // Add success message to chat
            const messageHtml = `
                <div class="flex justify-end mb-4">
                    <div class="bg-blue-500 text-white rounded-lg p-3 max-w-[70%] shadow">
                        <p class="text-sm">Rental terms set successfully.</p>
                    </div>
                </div>
            `;
            document.getElementById('chat-messages').insertAdjacentHTML('beforeend', messageHtml);
            scrollToBottom();
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
}); 