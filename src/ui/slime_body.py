"""
Slime Body Physics and Rendering Engine

Implements a blob-shaped AI avatar with physics simulation,
deformation, and interactive animations.
"""

import math
import numpy as np
from dataclasses import dataclass
from typing import Tuple, List, Optional
from enum import Enum


class AnimationState(Enum):
    """Animation states for the slime body"""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    ALERT = "alert"
    DANCING = "dancing"


@dataclass
class Vector2:
    """2D vector for physics calculations"""
    x: float
    y: float

    def __add__(self, other: 'Vector2') -> 'Vector2':
        return Vector2(self.x + other.x, self.y + other.y)

    def __mul__(self, scalar: float) -> 'Vector2':
        return Vector2(self.x * scalar, self.y * scalar)

    def magnitude(self) -> float:
        return math.sqrt(self.x ** 2 + self.y ** 2)

    def normalize(self) -> 'Vector2':
        mag = self.magnitude()
        if mag == 0:
            return Vector2(0, 0)
        return Vector2(self.x / mag, self.y / mag)


class SlimeBody:
    """
    Physics-based slime body with blob deformation and animation.
    
    Features:
    - Organic blob shape with smooth curves
    - Physics-based deformation responding to interactions
    - Particle effects for visual feedback
    - Color gradients (customizable)
    - Jiggle/breathing animation in idle state
    - Ripple effects on interaction
    """

    def __init__(
        self,
        position: Tuple[float, float],
        size: float = 100.0,
        color: str = "#00FFFF",
        segments: int = 32
    ):
        """
        Initialize the slime body.

        Args:
            position: (x, y) center position
            size: Base radius of the blob
            color: Hex color code
            segments: Number of segments for blob outline
        """
        self.position = Vector2(position[0], position[1])
        self.base_size = size
        self.current_size = size
        self.color = color
        self.segments = segments

        # Physics properties
        self.velocity = Vector2(0, 0)
        self.acceleration = Vector2(0, 0)
        self.mass = 1.0
        self.damping = 0.95

        # Deformation
        self.deformation_points = self._initialize_deformation_points()
        self.target_deformation = [0.0] * segments
        self.current_deformation = [0.0] * segments

        # Animation
        self.animation_state = AnimationState.IDLE
        self.animation_time = 0.0
        self.jiggle_intensity = 0.05
        self.breathing_speed = 2.0

        # Dance state
        self._dance_offset_x = 0.0   # horizontal bounce offset
        self._dance_offset_y = 0.0   # vertical bounce offset
        self._dance_spin     = 0.0   # rotation angle for deformation spin
        self._dance_scale    = 1.0   # size pulse

        # Ripple effect
        self.ripples: List[dict] = []
        self.ripple_damping = 0.98

    def _initialize_deformation_points(self) -> List[Vector2]:
        """Initialize deformation points around the blob perimeter"""
        points = []
        for i in range(self.segments):
            angle = (2 * math.pi * i) / self.segments
            x = self.base_size * math.cos(angle)
            y = self.base_size * math.sin(angle)
            points.append(Vector2(x, y))
        return points

    def update_physics(self, delta_time: float) -> None:
        """
        Update physics simulation.

        Args:
            delta_time: Time elapsed since last frame (seconds)
        """
        # Apply damping
        self.velocity = self.velocity * self.damping

        # Update position
        self.position = self.position + (self.velocity * delta_time)

        # Update deformation towards target
        for i in range(self.segments):
            diff = self.target_deformation[i] - self.current_deformation[i]
            self.current_deformation[i] += diff * 0.1  # Smooth interpolation

        # Update ripples
        for ripple in self.ripples[:]:
            ripple['age'] += delta_time
            ripple['amplitude'] *= self.ripple_damping

            if ripple['amplitude'] < 0.01:
                self.ripples.remove(ripple)

    def animate_jiggle(self, delta_time: float) -> None:
        """
        Apply jiggle/breathing/dancing animation based on current state.
        """
        self.animation_time += delta_time

        if self.animation_state == AnimationState.IDLE:
            breathing = math.sin(self.animation_time * self.breathing_speed) * 0.02
            self.current_size = self.base_size * (1.0 + breathing)
            for i in range(self.segments):
                jiggle = math.sin(self.animation_time * 3.0 + i) * self.jiggle_intensity
                self.target_deformation[i] = jiggle

        elif self.animation_state == AnimationState.DANCING:
            t = self.animation_time
            # Bounce up/down at ~2 Hz
            self._dance_offset_y = math.sin(t * 4.0 * math.pi) * 18.0
            # Sway left/right at ~1 Hz
            self._dance_offset_x = math.sin(t * 2.0 * math.pi) * 12.0
            # Spin the deformation pattern
            self._dance_spin = t * 3.0
            # Pulse size in sync with bounce
            self._dance_scale = 1.0 + math.sin(t * 4.0 * math.pi) * 0.12
            self.current_size = self.base_size * self._dance_scale
            # Squash-and-stretch deformation
            for i in range(self.segments):
                angle = (2 * math.pi * i) / self.segments + self._dance_spin
                wave = math.sin(angle * 2 + t * 8) * 0.25
                self.target_deformation[i] = wave

    def apply_force(self, force: Vector2, position: Vector2) -> None:
        """
        Apply a force to the slime body.

        Args:
            force: Force vector
            position: Position where force is applied (relative to blob center)
        """
        # Apply force to velocity
        acceleration = force * (1.0 / self.mass)
        self.velocity = self.velocity + acceleration

        # Calculate deformation based on force direction
        force_direction = force.normalize()
        force_magnitude = force.magnitude()

        # Find closest deformation point
        for i in range(self.segments):
            angle = (2 * math.pi * i) / self.segments
            point_dir = Vector2(math.cos(angle), math.sin(angle))

            # Dot product to determine influence
            influence = (
                point_dir.x * force_direction.x +
                point_dir.y * force_direction.y
            )

            if influence > 0:
                deformation = influence * force_magnitude * 0.1
                self.target_deformation[i] = max(
                    self.target_deformation[i],
                    deformation
                )

    def deform_on_interaction(
        self,
        interaction_point: Tuple[float, float],
        intensity: float = 1.0
    ) -> None:
        """
        Deform the slime body on user interaction.

        Args:
            interaction_point: (x, y) position of interaction
            intensity: Strength of deformation (0-1)
        """
        point = Vector2(interaction_point[0], interaction_point[1])
        direction = (point + (self.position * -1.0)).normalize()

        force = direction * (intensity * 50.0)
        self.apply_force(force, direction)

        # Add ripple effect
        self.apply_ripple_effect(interaction_point, intensity)

    def apply_ripple_effect(
        self,
        origin: Tuple[float, float],
        intensity: float = 1.0
    ) -> None:
        """
        Apply ripple effect emanating from a point.

        Args:
            origin: (x, y) origin of ripple
            intensity: Strength of ripple
        """
        ripple = {
            'origin': Vector2(origin[0], origin[1]),
            'age': 0.0,
            'amplitude': intensity,
            'wavelength': 20.0,
            'speed': 200.0
        }
        self.ripples.append(ripple)

    def set_animation_state(self, state: AnimationState) -> None:
        self.animation_state = state
        self.animation_time = 0.0
        self._dance_offset_x = 0.0
        self._dance_offset_y = 0.0

        if state == AnimationState.IDLE:
            self.jiggle_intensity = 0.05
        elif state == AnimationState.LISTENING:
            self.jiggle_intensity = 0.1
        elif state == AnimationState.PROCESSING:
            self.jiggle_intensity = 0.15
        elif state == AnimationState.ALERT:
            self.jiggle_intensity = 0.2
        elif state == AnimationState.DANCING:
            self.jiggle_intensity = 0.3

    def get_outline_points(self) -> List[Tuple[float, float]]:
        """
        Get the outline points of the slime body for rendering.

        Returns:
            List of (x, y) points forming the blob outline
        """
        outline = []

        for i in range(self.segments):
            angle = (2 * math.pi * i) / self.segments
            base_x = self.current_size * math.cos(angle)
            base_y = self.current_size * math.sin(angle)

            # Apply deformation
            deformation = self.current_deformation[i]
            deformed_x = base_x * (1.0 + deformation)
            deformed_y = base_y * (1.0 + deformation)

            # Apply ripple effects
            for ripple in self.ripples:
                distance = math.sqrt(
                    (deformed_x - ripple['origin'].x) ** 2 +
                    (deformed_y - ripple['origin'].y) ** 2
                )
                wave = (
                    math.sin(
                        distance / ripple['wavelength'] -
                        ripple['age'] * ripple['speed']
                    ) * ripple['amplitude']
                )
                deformed_x += wave * math.cos(angle)
                deformed_y += wave * math.sin(angle)

            # Add position offset (+ dance bounce offset)
            final_x = self.position.x + deformed_x + self._dance_offset_x
            final_y = self.position.y + deformed_y + self._dance_offset_y
            outline.append((final_x, final_y))

        return outline

    def set_color(self, color: str) -> None:
        """
        Set the slime body color.

        Args:
            color: Hex color code (e.g., "#00FFFF")
        """
        self.color = color

    def get_color_gradient(self) -> Tuple[str, str]:
        """
        Get color gradient for rendering (base and highlight).

        Returns:
            Tuple of (base_color, highlight_color)
        """
        # Simple gradient: base color and lighter version
        return (self.color, "#FFFFFF")

    def reset(self) -> None:
        """Reset the slime body to initial state"""
        self.position = Vector2(self.position.x, self.position.y)
        self.velocity = Vector2(0, 0)
        self.acceleration = Vector2(0, 0)
        self.current_size = self.base_size
        self.current_deformation = [0.0] * self.segments
        self.target_deformation = [0.0] * self.segments
        self.ripples = []
        self.animation_time = 0.0
