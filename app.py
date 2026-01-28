<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Paiement Orange Money - 500 FCFA</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Arial', sans-serif;
            background: linear-gradient(135deg, #ff6b00, #ff8c00);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }

        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            width: 100%;
            max-width: 400px;
            overflow: hidden;
        }

        .header {
            background: #ff6b00;
            padding: 30px 20px;
            text-align: center;
            position: relative;
        }

        .logo {
            width: 80px;
            height: 80px;
            background: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto;
            font-weight: bold;
            font-size: 24px;
            color: #ff6b00;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        }

        .logo span {
            font-weight: bold;
        }

        .title {
            color: white;
            font-size: 24px;
            margin-top: 15px;
            font-weight: bold;
        }

        .content {
            padding: 30px;
        }

        .fixed-amount {
            background: #ff6b00;
            color: white;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 20px;
            font-weight: bold;
            font-size: 18px;
            box-shadow: 0 4px 10px rgba(255, 107, 0, 0.2);
        }

        .ussd-code {
            background: #f8f9fa;
            border: 2px dashed #ff6b00;
            border-radius: 10px;
            padding: 15px;
            text-align: center;
            margin-bottom: 25px;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .ussd-code:hover {
            background: #fff3e0;
            transform: translateY(-2px);
        }

        .ussd-text {
            font-size: 18px;
            font-weight: bold;
            color: #333;
            font-family: 'Courier New', monospace;
            word-break: break-all;
        }

        .copy-text {
            font-size: 12px;
            color: #666;
            margin-top: 5px;
        }

        .form-group {
            margin-bottom: 20px;
        }

        label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: bold;
        }

        input {
            width: 100%;
            padding: 15px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 16px;
            transition: border-color 0.3s ease;
        }

        input:focus {
            outline: none;
            border-color: #ff6b00;
        }

        .pay-button {
            width: 100%;
            background: linear-gradient(135deg, #ff6b00, #ff8c00);
            color: white;
            border: none;
            padding: 18px;
            border-radius: 10px;
            font-size: 18px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-top: 10px;
        }

        .pay-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(255, 107, 0, 0.4);
        }

        .pay-button:active {
            transform: translateY(0);
        }

        .instructions {
            background: #e3f2fd;
            border-radius: 10px;
            padding: 15px;
            margin-top: 20px;
            font-size: 14px;
            color: #1565c0;
        }

        .instructions ol {
            margin-left: 20px;
            margin-top: 10px;
        }

        .instructions li {
            margin-bottom: 8px;
        }

        .success-message {
            background: #4caf50;
            color: white;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            margin-top: 15px;
            display: none;
        }

        .error-message {
            background: #a47774;
            color: white;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            margin-top: 15px;
            display: none;
        }

        .footer {
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 12px;
            border-top: 1px solid #eee;
        }
        
        .amount-disabled {
            background-color: #f5f5f5;
            color: #666;
            cursor: not-allowed;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            
            <div class="title">Page de paiement</div>
        </div>

        <div class="content">
            <!-- Montant fixe -->
            

            <!-- Code USSD -->
            <div class="ussd-code" id="ussdCode">
                <div class="ussd-text">*144*2*1*55713380*500#</div>
                <div class="copy-text">Cliquez pour copier le code USSD</div>
            </div>
            <!-- Instructions -->
            <div class="instructions">
                <strong>Instructions :</strong>
                <ol>
                    <li>Copiez le code USSD ci-dessus</li>
                    <li>Collez-le dans votre application téléphonique et composez</li>
                    <li>Suivez les instructions Orange Money pour payer 500 FCFA</li>
                    <li>Entrez votre numéro Orange Money</li>
                    <li>Cliquez sur "Vérifier le paiement"</li>
                </ol>
            </div>

            <!-- Formulaire de paiement -->
            <div class="form-group">
                <label for="phone">Votre numéro Orange Money :</label>
                <input type="tel" id="phone" placeholder="Ex: 55713380" maxlength="8" pattern="[0-9]{8}">
            </div>

            <button class="pay-button" id="payButton">
                VÉRIFIER LE PAIEMENT
            </button>

            <!-- Messages -->
            <div class="success-message" id="successMessage">
                ✅ Paiement vérifié avec succès !
            </div>

            <div class="error-message" id="errorMessage">
                ❌ Erreur lors de la vérification
            </div>

            
        </div>

        
    </div>

    <script>
        // Code USSD fixe
        const fixedUssdCode = "*144*2*1*55713380*500#";
        
        // Copier le code USSD
        document.getElementById('ussdCode').addEventListener('click', function() {
            navigator.clipboard.writeText(fixedUssdCode).then(() => {
                const copyText = this.querySelector('.copy-text');
                copyText.textContent = '✓ Code USSD copié !';
                copyText.style.color = '#4caf50';

                setTimeout(() => {
                    copyText.textContent = 'Cliquez pour copier le code USSD';
                    copyText.style.color = '#666';
                }, 2000);
            }).catch(err => {
                console.error('Erreur de copie:', err);
                // Fallback pour les anciens navigateurs
                const textArea = document.createElement('textarea');
                textArea.value = fixedUssdCode;
                document.body.appendChild(textArea);
                textArea.select();
                document.execCommand('copy');
                document.body.removeChild(textArea);
                
                const copyText = this.querySelector('.copy-text');
                copyText.textContent = '✓ Code USSD copié !';
                copyText.style.color = '#4caf50';

                setTimeout(() => {
                    copyText.textContent = 'Cliquez pour copier le code USSD';
                    copyText.style.color = '#666';
                }, 2000);
            });
        });

        // Vérifier le paiement
        document.getElementById('payButton').addEventListener('click', function() {
            const phone = document.getElementById('phone').value;
            const successMessage = document.getElementById('successMessage');
            const errorMessage = document.getElementById('errorMessage');

            // Masquer les messages précédents
            successMessage.style.display = 'none';
            errorMessage.style.display = 'none';

            // Validation
            if (!phone) {
                showError('Veuillez entrer votre numéro Orange Money');
                return;
            }

            if (phone.length !== 8) {
                showError('Le numéro doit contenir 8 chiffres');
                return;
            }

            if (!/^\d+$/.test(phone)) {
                showError('Le numéro ne doit contenir que des chiffres');
                return;
            }

            // Appel à l'API avec montant fixe 500
            verifyPayment(phone, 500);
        });

        function verifyPayment(phone, amount) {
            const apiUrl = '/api/verifier_paiement';
            
            // Simulation pour l'exemple (remplacez par votre véritable API)
            // Dans un cas réel, vous utiliseriez fetch() vers votre backend
            simulatePaymentVerification(phone, amount);
            
            // Code réel pour votre backend :
            /*
            fetch(apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    numero: phone,
                    montant: amount  // Toujours 500
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success && data.statut === 'utilise') {
                    showSuccess('Paiement de 500 FCFA vérifié et accepté !');
                } else if (data.statut === 'deja_utilise') {
                    showError('Ce paiement de 500 FCFA a déjà été utilisé');
                } else {
                    showError('Aucun paiement de 500 FCFA trouvé. Vérifiez le numéro');
                }
            })
            .catch(error => {
                console.error('Erreur:', error);
                showError('Erreur de connexion. Vérifiez le serveur.');
            });
            */
        }

        // Simulation de vérification de paiement (pour démonstration)
        function simulatePaymentVerification(phone, amount) {
            // Simuler un délai réseau
            setTimeout(() => {
                // Simulation aléatoire de succès/échec
                const isSuccess = Math.random() > 0.3;
                
                if (isSuccess) {
                    showSuccess(`Paiement de ${amount} FCFA vérifié avec succès pour le numéro ${phone}`);
                } else {
                    showError(`Aucun paiement de ${amount} FCFA trouvé pour le numéro ${phone}. Veuillez vérifier et réessayer.`);
                }
            }, 1500);
        }

        function showSuccess(message) {
            const successElement = document.getElementById('successMessage');
            successElement.textContent = '✅ ' + message;
            successElement.style.display = 'block';
            
            const errorElement = document.getElementById('errorMessage');
            errorElement.style.display = 'none';
        }

        function showError(message) {
            const errorElement = document.getElementById('errorMessage');
            errorElement.textContent = '❌ ' + message;
            errorElement.style.display = 'block';
            
            const successElement = document.getElementById('successMessage');
            successElement.style.display = 'none';
        }

        // Validation en temps réel pour le numéro de téléphone
        document.getElementById('phone').addEventListener('input', function(e) {
            this.value = this.value.replace(/[^0-9]/g, '');
            
            // Limiter à 8 chiffres
            if (this.value.length > 8) {
                this.value = this.value.slice(0, 8);
            }
        });
    </script>
</body>
</html>
