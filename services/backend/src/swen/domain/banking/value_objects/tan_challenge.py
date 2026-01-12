"""TAN Challenge value object."""

from pydantic import BaseModel, ConfigDict, Field


class TANChallenge(BaseModel):
    """TAN Challenge from the Bank."""

    challenge_text: str = Field(
        ...,
        min_length=1,
        description="Human-readable text what auth is for",
    )
    tan_method: str = Field(..., description="Tan ID based on protocol")
    tan_method_name: str = Field(..., description="e.g., 'SecureGo Puls'")

    # Optional fields depending on TAN method
    # TODO: THIS MIGHT BE DEPENDENT ON THE FINTS PROTOCOL, I AM NOT SURE WHETHER
    # ABSTRACTION MAKES SENSE HERE. PROBABLY IN THE BEGININNING IT IS FINE.
    hhduc_code: str | None = Field(default=None, description="optical TAN generators")
    matrix_code: tuple[str, bytes] | str | None = Field(
        default=None,
        description="For photo TAN (flickering barcode or image data tuple)",
    )

    # Transaction details for user verification
    reference: str = Field(default="", description="Transaction reference number")

    model_config = ConfigDict(
        frozen=True,  # Immutable
        str_strip_whitespace=True,
    )

    def __str__(self) -> str:
        parts = [
            f"TAN Challenge ({self.tan_method_name})",
            f"Challenge: {self.challenge_text}",
        ]

        if self.hhduc_code:
            parts.append(f"HHD_UC Code: {self.hhduc_code}")

        if self.matrix_code:
            parts.append("Matrix code available for photo TAN")

        if self.reference:
            parts.append(f"Reference: {self.reference}")

        return "\n".join(parts)
