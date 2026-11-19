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
		(ontable purple)
		(on green purple)
		(clear green)

		(ontable red)
		(clear red)
		(ontable orange)
		(clear orange)
		(ontable yellow)
		(clear yellow)
		(ontable blue)
		(clear blue)
	)
	(:goal (and (handempty robot)
		(ontable purple)
		(on red purple)
		(on blue red)
		(on orange blue)
		(clear orange)
		(ontable yellow)
		(clear yellow)

		(ontable green)
		(clear green)
	))
)