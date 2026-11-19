(define (problem blocksworld)
	(:domain blocksworld)
	(:objects
		blue - block
		green - block
		orange - block
		purple - block
		red - block
		yellow - block
		robot - robot
	)
	(:init (handempty robot)
		(ontable red)
		(clear red)
		(ontable orange)
		(clear orange)
		(ontable yellow)
		(clear yellow)
		(ontable green)
		(clear green)
		(ontable blue)
		(clear blue)
		(ontable purple)
		(clear purple)
	)
	(:goal (and (handempty robot)
		(ontable purple)
		(on red purple)
		(clear red)
		(ontable green)
		(clear green)
		(ontable orange)
		(clear orange)

		(ontable blue)
		(on yellow blue)
		(clear yellow)
	))
)