(() => {
  const form = document.getElementById('signup-form');
  if (!form) return;

  const password = form.elements.password;
  const confirmation = form.elements.confirm_password;
  const passwordFeedback = document.getElementById('password-feedback');
  const confirmFeedback = document.getElementById('confirm-feedback');

  const passwordProblems = () => {
    const value = password.value;
    const problems = [];
    if (value.length < 12) problems.push('at least 12 characters');
    if (value.length > 256) problems.push('no more than 256 characters');
    if (!/[A-Z]/.test(value)) problems.push('an uppercase letter');
    if (!/[a-z]/.test(value)) problems.push('a lowercase letter');
    if (!/\d/.test(value)) problems.push('a number');
    if (!/[^A-Za-z0-9]/.test(value)) problems.push('a symbol');
    return problems;
  };

  const updateConfirmation = () => {
    if (!confirmation.value) {
      confirmFeedback.textContent = '';
      return confirmation.required;
    }
    const matches = password.value === confirmation.value;
    confirmFeedback.textContent = matches ? 'Passwords match.' : 'Passwords do not match yet.';
    return matches;
  };

  password.addEventListener('input', () => {
    passwordFeedback.textContent = '';
    updateConfirmation();
  });
  confirmation.addEventListener('input', updateConfirmation);

  form.addEventListener('submit', (event) => {
    if (!form.checkValidity()) {
      event.preventDefault();
      form.reportValidity();
      return;
    }

    const problems = passwordProblems();
    if (problems.length) {
      event.preventDefault();
      passwordFeedback.textContent = `Password needs ${problems.join(', ')}.`;
      password.focus();
      passwordFeedback.scrollIntoView({ block: 'center', behavior: 'smooth' });
      return;
    }

    if (!updateConfirmation()) {
      event.preventDefault();
      confirmation.focus();
      confirmFeedback.scrollIntoView({ block: 'center', behavior: 'smooth' });
    }
  });
})();
