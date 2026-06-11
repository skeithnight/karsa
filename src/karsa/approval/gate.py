class HumanGate:
    def wait_for_approval(self, prompt_message: str = "Do you approve? (approve/reject): ") -> bool:
        while True:
            response = input(prompt_message).strip().lower()
            if response == "approve":
                return True
            elif response == "reject":
                return False
            else:
                print("Invalid input. Please type 'approve' or 'reject'.")
